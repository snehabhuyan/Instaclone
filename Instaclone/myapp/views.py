from django.shortcuts import render, redirect
from forms import SignUpForm, LoginForm, PostForm, LikeForm, CommentForm
from models import UserModel, SessionToken, PostModel, LikeModel, CommentModel
from django.contrib.auth.hashers import make_password, check_password
from datetime import timedelta
from django.utils import timezone
from Instaclone.settings import BASE_DIR
from clarifai.rest import ClarifaiApp, Image as ClImage
import requests

from imgurpython import ImgurClient

YOUR_CLIENT_ID='61f881177fe7804'
YOUR_CLIENT_SECRET ='40f211398fdac41c4120da2d8f77227ac98384ee'
PARALLEL_DOTS_KEY = '5d1i6JwqibzZaZJrgAW84Fb6VdSpwmVxRD5xvcAA6VE'

# Create your views here.

def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            # saving data to DB
            user = UserModel(name=name, password=make_password(password), email=email, username=username)
            user.save()
            return render(request, 'success.html')
            # return redirect('login/')
    else:
        form = SignUpForm()

    return render(request, 'index.html', {'form': form})


def login_view(request):
    response_data = {}
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = UserModel.objects.filter(username=username).first()

            if user:
                if check_password(password, user.password):
                    token = SessionToken(user=user)
                    token.create_token()
                    token.save()
                    response = redirect('feed/')
                    response.set_cookie(key='session_token', value=token.session_token)
                    return response
                else:
                    response_data['message'] = 'Incorrect Password! Please try again!'

    elif request.method == 'GET':
        form = LoginForm()

    response_data['form'] = form
    return render(request, 'login.html', response_data)


def post_view(request):
    user = check_validation(request)

    if user:
        if request.method == 'POST':
            form = PostForm(request.POST, request.FILES)
            if form.is_valid():
                image = form.cleaned_data.get('image')
                caption = form.cleaned_data.get('caption')
                post = PostModel(user=user, image=image, caption=caption)
                post.save()

                path = str(BASE_DIR + '/' + post.image.url)

                client = ImgurClient(YOUR_CLIENT_ID, YOUR_CLIENT_SECRET)
                post.image_url = client.upload_from_path(path, anon=True)['link']
                post.save()
                app = ClarifaiApp(api_key='fb55a24f035040a3a86ed081b89bb64c')
                model = app.models.get('e9576d86d2004ed1a38ba0cf39ecb4b1')
                image = ClImage(url=post.image_url)
                response = model.predict([image])
                sfw_value = response['outputs'][0]['data']['concepts'][0]['value']
                print "The value for SFW is: " , sfw_value
                nsfw_value = response['outputs'][0]['data']['concepts'][1]['value']
                print "The value for NSFW is: " , nsfw_value

                if nsfw_value > 0.50:
                    print "do not show the image"
                else:
                    print "show image"



                return redirect('/feed/')

        else:
            form = PostForm()
        return render(request, 'post.html', {'form': form})
    else:
        return redirect('/login/')


def feed_view(request):
    user = check_validation(request)
    if user:

        posts = PostModel.objects.all().order_by('created_on')

        for post in posts:
            existing_like = LikeModel.objects.filter(post_id=post.id, user=user).first()
            if existing_like:
                post.has_liked = True

        return render(request, 'feed.html', {'posts': posts})
    else:

        return redirect('/login/')


def like_view(request):
    user = check_validation(request)
    if user and request.method == 'POST':
        form = LikeForm(request.POST)
        if form.is_valid():
            post_id = form.cleaned_data.get('post').id
            existing_like = LikeModel.objects.filter(post_id=post_id, user=user).first()
            if not existing_like:
                LikeModel.objects.create(post_id=post_id, user=user)
            else:
                existing_like.delete()
            return redirect('/feed/')
    else:
        return redirect('/login/')


def comment_view(request):
    user = check_validation(request)
    abuse_msg= "nothing"
    if user and request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            post_id = form.cleaned_data.get('post').id
            comment_text = form.cleaned_data.get('comment_text')

            print checkComment(comment_text)
            if checkComment(comment_text)==1:
                comment = CommentModel.objects.create(user=user, post_id=post_id, comment_text=comment_text)
                comment.save()
            else:
                abuse_msg="please use appropriate language"
            return redirect('/feed/', {'abuse_msg':abuse_msg})
        else:
            return redirect('/feed/')
    else:
        return redirect('/login')

# method for checking if comment is appropriate or abusive

def checkComment(commenttext):
    req_json= None
    req_url= "https://apis.paralleldots.com/abuse"
    payload = {
        "text": commenttext,
        "apikey": PARALLEL_DOTS_KEY
    }


# 1 For appropriate words and 0 for abusive words

    try:
        req_json= requests.post(req_url, payload).json()
    except:
        print""


    if req_json is not None:
        #sentiment= req_json['sentiment']
        print req_json['sentence_type']
        print req_json['confidence_score']
        if req_json['sentence_type']=="appropriate":
            if req_json['confidence_score']> 0.60:
                return 1
            else:
                return 0
        else:
            return 0

    return 0

#method to check image

#def checkpic_view():
#    app= ClarifaiApp(api_key='fb55a24f035040a3a86ed081b89bb64c')
#    model = app.models.get('general-v1.3')
#    image = model.predict_by_url(url=post.image_url)
#
#method to logout user of his account

def logoutuser_view(request):
    user= check_validation(request)

    if user is not None:
        latest_session= SessionToken.objects.filter(user=user).last()
        if latest_session:
            latest_session.delete()
            return redirect('/login')

def upvote_view(request):
    if request.method=="POST":
        print 'x'





# For validating the session
def check_validation(request):
    if request.COOKIES.get('session_token'):
        session = SessionToken.objects.filter(session_token=request.COOKIES.get('session_token')).first()
        if session:
            time_to_live = session.created_on + timedelta(days=1)
            if time_to_live > timezone.now():
                return session.user
    else:
        return None