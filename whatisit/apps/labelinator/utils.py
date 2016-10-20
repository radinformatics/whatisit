from django.core.files.uploadedfile import UploadedFile, InMemoryUploadedFile
from django.core.files.base import ContentFile
from whatisit.apps.labelinator.models import Report
from whatisit.settings import MEDIA_ROOT
from whatisit.apps.labelinator.models import AllowedAnnotation
from django.core.files import File
import shutil
import os
import re

def get_annotation_counts(collection):
    '''get_annotation_counts will return a dictionary with annotation labels, values,
    and counts for all allowed_annotations for a given collection
    :param collection: the collection to get annotation counts for
    '''
    # What annotations are allowed across the report collection?
    annotations_allowed =  AllowedAnnotation.objects.filter(annotation__reports__collection=collection)

    # Take a count
    counts = dict()
    total = 0
    for annotation_allowed in annotations_allowed:
        if annotation_allowed.name not in counts:
            counts[annotation_allowed.name] = {}
        report_n = annotation_allowed.annotation_set.values_list('reports', flat=True).distinct().count()
        counts[annotation_allowed.name][annotation_allowed.label] = report_n
        total += report_n
    counts['total'] = total

    return counts    


#TODO: edit these to upload reports 
def save_image_upload(collection,image,report=None):
    '''save_image_upload will save an image object to a collection
    :param collection: the collection object
    :param report: the report object, e.g., if updating
    '''
    if report==None:
        report = report(collection=collection)
    collection_dir = "%s/%s" %(MEDIA_ROOT,collection.id)
    if not os.path.exists(collection_dir):
        os.mkdir(collection_dir)
    report_file = '%s/%s' %(collection_dir,image.name)
    with open(report_file, 'wb+') as destination:
        for chunk in image.chunks():
            destination.write(chunk)
    report.name = image.name
    report.version = get_image_hash(report_file)
    report.image = image
    report.image.name = image.name
    report.save()
    return report


def save_package_upload(collection,image,report=None):
    '''save_package_upload will save an image object extracted from a package to a collection
    this is currently not in use, as most users will not package reports.
    :param collection: the collection object
    :param report: the report object, e.g., if updating
    '''
    if report==None:
        report = report(collection=collection)
    collection_dir = "%s/%s" %(MEDIA_ROOT,collection.id)
    if not os.path.exists(collection_dir):
        os.mkdir(collection_dir)
    report_file = '%s/%s' %(collection_dir,image.name)
    with open(report_file, 'wb+') as destination:
        for chunk in image.chunks():
            destination.write(chunk)
    report.name = image.name
    report.version = get_image_hash(report_file)
    report.image = image
    report.image.name = image.name
    report.save()
    return report


def save_package(collection,package,report=None):
    '''save_package_upload will save a package object to a collection
    by way of extracting the image to a temporary location, and
    adding meta data to the report
    :param collection: the collection object
    :param package: the full path to the package
    :param report: the report object, e.g., if updating
    '''
    if report==None:
        report = report(collection=collection)
    collection_dir = "%s/%s" %(MEDIA_ROOT,collection.id)
    if not os.path.exists(collection_dir):
        os.mkdir(collection_dir)
    # Unzip the package image to a temporary directory
    includes = list_package(package)
    image_path = [x for x in includes if re.search(".img$",x)]
    # Only continue if an image is found in the package
    if len(image_path) > 0:
        image_path = image_path[0]
        # The new file will be saved to the collection directory
        new_file = '%s/%s' %(collection_dir,image_path)
        contents = load_package(package)
        tmp_file = contents[image_path]
        report.name = image_path
        report.version = get_image_hash(tmp_file)
        image = File(open(tmp_file,'rb'),image_path)
        with open(new_file, 'wb+') as destination:
            for chunk in image.chunks():
                destination.write(chunk)
        report.image = new_file
        report.save()
        # Add the report to the collection
        collection.report_set.add(report)
        collection.save
        # Clean up temporary directory
        shutil.rmtree(os.path.dirname(tmp_file))
        return report
    return None


def add_message(message,context):
    '''add_message will add a message to the context
    :param message: the message (list or string) to add
    :param context: the context (dict) for the template view
    '''
    # Messages must be in a list
    if message != None:
        if not isinstance(message,list):
            message = [message]
        context["messages"] = message
    return context


def format_report_name(name,special_characters=None):
    '''format_report_name will take a name supplied by the user,
    remove all special characters (except for those defined by "special-characters"
    and return the new image name.
    '''
    if special_characters == None:
        special_characters = []
    return ''.join(e.lower() for e in name if e.isalnum() or e in special_characters)


