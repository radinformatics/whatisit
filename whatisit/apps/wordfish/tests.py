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
    ReportSet,
    ReportCollection,
    Report
)

from whatisit.apps.wordfish.views import (
    get_permissions,
    view_report_collection
)

from whatisit.apps.wordfish.utils import (
    get_report_set,
    get_report_collection,
    get_report,
    select_random_reports
)

from whatisit.apps.users.utils import (
    get_annotation_status,
    get_credential,
    get_user,
    needs_testing
)

def test_annotator(request,rid,uid):
    '''test_annotator will ask an annotator to answer the specified number of
    questions to be granted access to annotate a collection. The data is stored
    in a session, and the session expires (and is reset) when the user has viewed
    the total number of required questions
    :param rid: the id of the report set
    :param uid: the user id to be tested
    '''
    user = get_user(uid)
    report_set = get_report_set(rid)
    permissions = get_permissions(collection=report_set.collection)

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

            # Check for session variable
            testing_set = request.session.get('reports_testing_set', None)
            testing_correct = request.session.get('reports_testing_correct', None)
            testing_incorrect = request.session.get('reports_testing_incorrect', None)

            # Total reports required for taking, and for passing
            N = report_set.number_tests
            N_pass = report_set.passing_tests

            # Undefined session means the user hasn't created a set yet

            ###########################################################
            # NEW TESTING SESSION
            ###########################################################
            if testing_set == None:
                messages.info(request, 'This is the start of the test. You will be asked to annotate %s reports.' %(N))   
          
                # Set the testing_correct, testing_incorrect to 0
                request.session['reports_testing_incorrect'] = 0
                request.session['reports_testing_correct'] = 0

                # Randomly select N reports from the set
                testing_reports = select_random_reports(reports=report_set.reports,
                                                        N=N)
                # Remove the first for testing
                testing_report = testing_reports.pop(0)
                request.session['reports_testing'] = testing_reports

                # Start testing the user
                context = {"report":testing_report}
                return render(request, "testing/testing_report_set.html", context)


            ###########################################################
            # RESUME TESTING SESSION
            ###########################################################       
            else:
                # If the testing set session is not empty, get any updated answers
                if request.method == "POST":

                    #labels = request.POST.get(..)
                    #number_correct = score_count_correct(labels...)
                    #number_incorrect = len(labels) - number_correct

                    # Update the number correct
                    testing_correct = testing_correct + number_correct

                    # If the testing set has length 0, we finished
                    if len(testing_set) == 0:
                   
                        # Did the user pass?
                        if testing_correct >= N_pass:
                            user_status = credential.status = "APPROVED"
                        else:
                            user_status = credential.status = "DENIED"
                        credential.save()                            
                            
                    # The user is still testing, update the counts
                    else:
                        request.session['reports_testing_correct'] = testing_correct
                        request.session['reports_testing_incorrect'] = testing_incorrect
                        

        # If the user status was approved, either previously or aboved, move on to annotation
        if user_status == "APPROVED":
            messages.info(request,"Congratulations, you have passed the testing! You are now annotating the collection set.")

            # Make sure their testing session is removed
            request.session['reports_testing_incorrect'] = None
            request.session['reports_testing_incorrect'] = None
            request.session['reports_testing'] = None
            return annotate_set(request,report_set.id)




        # TODO: make this view: return render(request, "testing/testing_report_set.html", context)
        # TODO: need to add POST here in case user has submit testing view to move on to next, and update session

    # User does not have permission to annotate, return to collection view
    else:
        messages.info(request,"You do not have permissions to perform this operation.")
    
    # Denied, or not annotate permission returns to see collection
    return view_report_collection(request,report_set.collection.id)