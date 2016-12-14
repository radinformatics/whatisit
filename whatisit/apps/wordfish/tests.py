from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models.aggregates import Count
from django.forms.models import model_to_dict
from django.http import HttpResponse, JsonResponse
from django.http.response import (
    HttpResponseRedirect, 
    HttpResponseForbidden, 
    Http404
)

from django.shortcuts import (
    get_object_or_404, 
    render_to_response, 
    render, 
    redirect
)

from whatisit.apps.wordfish.models import (
    Annotation,
    AllowedAnnotation,
    ReportSet,
    ReportCollection,
    Report
)

from whatisit.apps.wordfish.utils import (
    get_annotations,
    get_report_set,
    get_report_collection,
    get_report,
    select_random_reports,
    summarize_annotations
)

from whatisit.apps.users.utils import (
    get_annotation_status,
    get_credential,
    get_user,
    needs_testing
)

import pickle
import re

def test_annotator(request,sid,rid=None):
    '''test_annotator will ask an annotator to answer the specified number of
    questions to be granted access to annotate a collection. The data is stored
    in a session, and the session expires (and is reset) when the user has viewed
    the total number of required questions
    :param sid: the id of the report set
    :param rid: the report id that was tested
    '''
    from whatisit.apps.wordfish.views import (
       annotate_report,
       get_permissions,
       view_report_collection
    )
    from whatisit.apps.users.models import Credential

    if rid != None: # scoring is needed
        completed_report = get_report(request,rid)
    
    user = request.user

    report_set = get_report_set(request,sid)
    context = {'collection':report_set.collection}
    permissions = get_permissions(request,context)

    # Double check that user has permission to annotate
    if permissions["annotate_permission"] == True:
   
        # Also check that user hasn't previously failed.
        credential = Credential.objects.get(user=user,
                                            report_set=report_set)

        # Double check user status
        user_status = get_annotation_status(report_set=report_set,
                                            user=user)

        # Only continue if user_status is TESTING
        if user_status == "TESTING":

            # Get session variable
            session = get_testing_session(request=request,
                                          user=user,
                                          report_set=report_set)

            testing_report = None
            testing_set = session.get('reports_testing', None)
            testing_correct = session.get('reports_testing_correct', None)
            testing_incorrect = session.get('reports_testing_incorrect', None)

            # Total reports required for taking, and for passing
            N = report_set.number_tests
            N_pass = report_set.passing_tests

            # Undefined session means the user hasn't created a set yet
            res = {'correct':testing_correct,'wrong':testing_incorrect,'set':testing_set}
            pickle.dump(res,open('testing-set.pkl','wb'))

            ###########################################################
            # NEW TESTING SESSION
            ###########################################################
            if testing_set == None:
                messages.info(request, '''This is the start of the test. You will be asked to annotate %s reports.
                                       You should click on the correct label below, and then you can 
                                       use your right arrow key (or the arrow at the bottom) to submit your answer.
                                       ''' %(N))   
          
                # Set the testing_correct, testing_incorrect to 0
                session['reports_testing_incorrect'] = 0
                session['reports_testing_correct'] = 0

                # Randomly select N reports from the set
                testing_reports = select_random_reports(reports=report_set.reports.all(),
                                                        N=N)
                testing_reports = list(testing_reports)

                # Remove the first for testing
                testing_report = testing_reports.pop(0)
                session['reports_testing'] = testing_reports


            ###########################################################
            # RESUME TESTING SESSION
            ###########################################################       
            else:
                # If the testing set session is not empty, get any updated answers
                if request.method == "POST":

                    # Get the correct annotations from the database
                    correct_annotations = get_annotations(user=report_set.gold_standard,
                                                          report=completed_report)
                    answers = summarize_annotations(correct_annotations)['labels']

                    post_keys = list(request.POST.keys())
                    for post_key in post_keys:
                        # The annotation labels have a '||'
                        if re.search('[||]',post_key):
                            new_annotation = request.POST[post_key]
                            user_selected = False
                            if new_annotation == "on":
                                selected_name,selected_label = post_key.split('||')               
                                user_selected = True   

                            # If we have an answer
                            if selected_name in answers:
                                correct_answer = answers[selected_name]

                                # The user selected the right answer
                                if user_selected and correct_answer == selected_label:
                                    testing_correct += 1 

                                # The user selected, but not right answer
                                elif user_selected and correct_answer != selected_label:
                                    testing_incorrect += 1 
                            
                                # The user didn't select, is right answer
                                elif not user_selected and correct_answer == selected_label:
                                    testing_incorrect += 1 

                                # The user didn't select, is not right answer
                                elif not user_selected and correct_answer != selected_label:
                                    continue
                

                    # If the total number tests (correct and incorrect)
                    if len(testing_set) == 0:
                   
                        # Did the user pass?
                        if testing_correct >= N_pass:
                            user_status = credential.status = "APPROVED"
                        else:
                            user_status = credential.status = "DENIED"
                        credential.save()                            
                            
                    # The user is still testing, update the counts
                    else:
                        session['reports_testing_correct'] = testing_correct
                        session['reports_testing_incorrect'] = testing_incorrect
                        

        # If user status is (still) TESTING, start or continue
        if user_status == "TESTING":

            # If we didn't select a testing report
            if testing_report == None:
                testing_report = testing_set.pop(0)
                session['reports_testing'] = testing_set
           
            # Update the user with remaining reports
            remaining_tests = N - (testing_correct + testing_incorrect)
            messages.info(request,'You have %s reports remaining in this session' %(remaining_tests))

            # Get allowed annotations for set
            testing_annotations = get_testing_annotations(report_set)

            # Start testing the user
            return annotate_report(request=request,
                                   rid=testing_report.id,
                                   sid=report_set.id,
                                   report=testing_report,
                                   allowed_annotations=testing_annotations,
                                   template="annotate/testing_random.html")

        # If the user status was approved, either previously or aboved, move on to annotation
        elif user_status == "APPROVED":
            messages.info(request,"Congratulations, you have passed the testing! You are now annotating the collection set.")
            request = clear_testing_session(request) # Sets all to None
            delete_testing_session(user,report_set)
            return annotate_set(request,report_set.id)

        elif user_status == "DENIED":
            messages.info(request,"You are not qualified to annotate this set.")
            request = clear_testing_session(request) # Sets all to None
            delete_testing_session(user,report_set)
            return view_report_collection(request,report_set.collection.id)
           

    # User does not have permission to annotate, return to collection view
    else:
        messages.info(request,"You do not have permissions to perform this operation.")
    
    # Denied, or not annotate permission returns to see collection
    return view_report_collection(request,report_set.collection.id)



def clear_testing_session(request,update_value=None):
    '''clear_testing_session will return a request with the testing session
    cleared (value of None). If update_value is specified, this value is used
    instead 
   '''
    # Make sure their testing session is removed
    request.session['reports_testing_incorrect'] = update_value
    request.session['reports_testing_incorrect'] = update_value
    request.session['reports_testing'] = update_value
    return request


def delete_testing_session(user,report_set=None):
    '''delete one or (all) testing sessions for a user, allowing
    him or her to restart tests (given that the credential objects 
    are updated appropriately). If no report_set is provided, all
    sessions are deleted
    :param user: a User object
    :param report_set: a report set (optional)
    '''
    from whatisit.apps.users.models import TestingSession
    if not report_set:
        testing_session = TestingSession.objects.filter(user=user)
    else:
        testing_session = [TestingSession.objects.get(user=user,
                                                      report_set=report_set)]
    for session in testing_session:
        session.session.delete()
        session.delete()


def get_testing_session(request,user,report_set):
    '''get_testing_session retrieves a testing session, where a particular request.session
    is linked to the TestingSession.session variable. If not created, the current from the
    request is linked, and the object saved. If created, the same session variable is returned. 
    '''
    from whatisit.apps.users.models import TestingSession
    testing_session,created = TestingSession.objects.get_or_create(user=user, 
                                                                   report_set=report_set)
            
    # If created is True, it's a new session
    if created == True:
        testing_session.session = request.session
        testing_session.save()
    return testing_session.session


def get_testing_annotations(report_set):
    '''get_testing_annotations will first get the unique label names (eg, diagnosis) that 
    the user has selected for a report set, but return ALL possible labels (eg, positive/negative)
    to test the user. This is to ensure that testing scoring is not biased on one label type
    '''
    set_annotations = report_set.testing_annotations.all()
    label_names = []
    for set_annotation in set_annotations:
        if set_annotation.name not in label_names:
            label_names.append(set_annotation.name)

    # Get allowed annotations, note that report set above already filtered to collection
    allowed_annotations = AllowedAnnotation.objects.filter(name__in=label_names)
    if len(allowed_annotations) == 0:
        return None
    return allowed_annotations
