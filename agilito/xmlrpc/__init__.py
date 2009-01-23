from xmlrpc import public
from django.contrib.auth.models import User
from agilito.models import UserStory

CATEGORY_STORY = 1

def authenticate(username, password):
    try:
        user = User.objects.filter(username=username)[0]
        if user.check_password(password):
            return user
    except IndexError:
        pass

    raise Exception('username/password not recognized')

def getProject(user, id):
    projects = user.project_set.all()
    if projects is None or projects.count() == 0:
        raise Exception('You do not belong to any projects')

    id = int(id)
    for project in projects:
        if project.id == id:
            return project
    raise Exception('You are not assigned to project %s' % id)

def story2post(user, story):
    return {
            'link': story.get_absolute_url(),
            'permaLink': story.get_absolute_url(),
            'userid': user.id,
            'postid': story.id,
            'title': story.name,
            'description': story.description,
            'categories': [CATEGORY_STORY]
           }
@public
def metaWeblog_newPost(blogid, username, password, struct, publish):
    user = authenticate(username, password)

    projectID, category = blogid.split(':')
    project = getProject(user, projectID)

    story = UserStory()
    story.project = project
    story.name = struct['title']
    story.description = struct['description']
    story.save()

    return str(story.id)

@public
def metaWeblog_editPost(postid, username, password, struct, publish):
    user = authenticate(username, password)
    story = UserStory.objects.filter(id=int(postid))[0]
    getProject(user, story.project.id)

    story.name = struct['title']
    story.description = struct['description']
    story.save()

@public
def metaWeblog_getPost(postid, username, password):
    user = authenticate(username, password)
    story = UserStory.objects.filter(id=int(postid))[0]

    getProject(user, story.project.id)

    return story2post(user, story)

@public
def metaWeblog_getCategories(blogid, username, password):
    user = authenticate(username, password)
    return [{'description': 'User stories', 'categoryid': CATEGORY_STORY, 'title': 'User stories'}]

@public
def metaWeblog_getRecentPosts(blogid, username, password, numberOfPosts):
    user = authenticate(username, password)
    
    projectID, category = blogid.split(':')

    if category != 'story':
        raise Exception('Unsupported category "%s"' % category)

    project = getProject(user, projectID)

    if numberOfPosts == 0:
        stories = UserStory.objects.filter(project=project, iteration=None)
    else:
        stories = UserStory.objects.filter(project=project, iteration=None)[:numberOfPosts] 
    posts = []
    for story in stories:
        posts.append(story2post(user, story))
    return posts

@public
def blogger_getUsersBlogs(appid, username, password):
    user = authenticate(username, password)
    projects = user.project_set.all()
    if projects is None or projects.count() == 0:
        raise Exception('You do not belong to any projects')

    blogs = []
    for project in projects:
        blog = {}
        blog['url'] = 'http://10.168.1.1:8000/%d/iteration/' % project.id
        blog['blogid'] = '%d:story' % project.id
        blog['blogName'] = project.name

        blogs.append(blog)
    return blogs

@public
def blogger_getUserInfo(appid, username, password):
    user = authenticate(username, password)
    return [{
                'nickname': user.username,
                'userid': user.id,
                'url': user.get_absolute_url(),
                'email': user.email,
                'firstname': user.first_name,
                'lastname': user.last_name
                }]

