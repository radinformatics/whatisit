from django.http import JsonResponse
from whatisit.apps.main.utils import write_file

from datetime import datetime
from git import Repo
import shutil
import tempfile


def chooseJsonResponse(response,json_response=True,status=None):
    '''chooseJsonResponse will return either a json response, 
    or just the json
    :param response: the response dictionary to serialize to json
    :param json_response: return a json response (True), or just json (False)
    :param status: a status code (not required)
    '''
    if json_response == True:
        if status == None:
            return JsonResponse(response)
        return JsonResponse(response,status=status)
    return response


def download_repo(repo_url,destination):
    '''download_repo
    Download a github repo to a "destination"
    :param repo_url: should be the URL for the repo.
    :param destination: the full path to the destination for the repo
    '''
    return Repo.clone_from(repo_url, destination)


def run_travis_build(container,travis_repo="https://github.com/singularityware/hello-world"):
    '''run_travis_build will take the Singularity file from a Container model (the spec)
    and send it to continuous integration for building and testing via cloning a temporary repo
    UNDER TESTING
    :param container: the Singularity container object
    :param travis_repo: the Github URL that has a .travis.yml with tests
    '''
    # Get the experiment selection, and install the experiment for the user
    tmpdir = tempfile.mkdtemp()
    repo = download_repo(repo_url=travis_repo,
                         destination=tmpdir)

    # Checkout new branch
    branch_name = "test/%s" %(container.name)
    new_branch = repo.create_head(branch_name)
    new_branch.checkout()

    # Write spec to folder
    singularity_file = write_file(filename="%s/Singularity" %(tmpdir), 
                                  content=str.encode(container.spec))

    # Commit, push, and PR
    log = repo.index.add([singularity_file])[0]
    # (100644, e69de29bb2d1d6434b8b29ae775ad8c2e48c5391, 0, Singularity)

    # Commit the changes to deviate masters history
    now = str(datetime.now())
    commit = repo.index.commit("Testing %s for container build: %s" %(container.name,now))
    
    # Create remote branch and push
    origin = repo.create_remote(branch_name, url=repo.working_tree_dir)

    #commit = repo.commit('master').__str__()
    # STOPPED HERE - how to do PR without having a million branches?

    # Remove the temporary directory, return message
    shutil.rmtree(tmpdir)
