import re
import datetime
from bson import ObjectId
from flask import Flask, request, redirect, render_template, session
import pymongo
import os.path
import random

from Mail import send_email

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
PROFILE_PATH = APP_ROOT + "/static/pictures"
POSTER_PATH = APP_ROOT + "/static/poster"
SONG_PATH = APP_ROOT + "/static/song"
SONG_POSTER_PATH = APP_ROOT + "/static/song_poster"
my_client = pymongo.MongoClient("mongodb://localhost:27017")
my_database = my_client["music"]
admin_col = my_database["admin"]
band_col = my_database["band"]
user_col = my_database["user"]
genre_col = my_database["genre"]
album_col = my_database["album"]
song_col = my_database["song"]
playlist_col = my_database["playlist"]
transaction_col = my_database["transaction"]
payment_col = my_database["payment"]
subscription_col = my_database["subscription"]

app = Flask(__name__)
app.secret_key = "chandra"

admin_username = "admin"
admin_password = "admin"

audio_formats = [".mp3"]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/admin_login")
def admin_login():
    return render_template("admin_login.html")


@app.route("/admin_login_action", methods=['post'])
def admin_login_action():
    username = request.form.get("username")
    password = request.form.get("password")
    if username == admin_username and password == admin_password:
        session['role'] = "admin"
        return redirect("/admin_home")
    else:
        return render_template("message.html", message="invalid login")


@app.route("/admin_home")
def admin_home():
    return render_template("admin_home.html")


@app.route("/view_band")
def view_band():
    query = {}
    bands = band_col.find(query)
    bands = list(bands)
    return render_template("view_band.html",bands=bands)


@app.route("/verify")
def verify():
    band_id = request.args.get("band_id")
    query1 = {"_id":ObjectId(band_id)}
    query2 = {"$set":{"status": "verified"}}
    band_col.update_one(query1, query2)
    return redirect("/view_band")


@app.route("/unverified")
def unverified():
    band_id = request.args.get("band_id")
    query = {"_id":ObjectId(band_id)}
    query2 = {"$set":{"status":"deactivated"}}
    band_col.update_one(query, query2)
    return view_band()



@app.route("/add_genre")
def add_genre():
    message = request.args.get("message")
    if message == None:
        message = ""
    genres = genre_col.find()
    return render_template("add_genre.html",genres=genres, message=message)


@app.route("/add_genre_action",methods=['post'])
def add_genre_action():
    genre_name = request.form.get("genre_name")
    query = {"$or":[{"genre_name":genre_name}]}
    count = genre_col.count_documents(query)
    if count > 0:
        return redirect("/add_genre?message=Duplicate Genre Name")
    else:
        genre_col.insert_one({"genre_name": genre_name})
        return redirect("/add_genre?message=Genre Added Successfully")


@app.route("/edit_genre")
def edit_genre():
    genre_id = request.args.get("genre_id")
    return render_template("edit_genre.html",genre_id=genre_id)


@app.route("/edit_genre_action",methods=['post'])
def edit_genre_action():
    genre_id = request.form.get("genre_id")
    genre_name = request.form.get("genre_name")
    print(genre_id)
    query = {"_id": ObjectId(genre_id)}
    query2 = {"$set":{"genre_name":genre_name}}
    genre_col.update_one(query, query2)
    print(query2)
    return redirect("/add_genre")


@app.route("/band_registration")
def band_registration():
    return render_template("band_login.html")


@app.route("/band_registration_action", methods=['post'])
def band_registration_action():
    # band_firstname = request.form.get("band_firstname")
    # band_lastname = request.form.get("band_lastname")
    band_name = request.form.get("band_name")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")
    if password != confirm_password:
        return render_template("message.html",message="Password Didn't Match")
    email = request.form.get("email")
    address = request.form.get("address")
    zipcode = request.form.get("zipcode")
    phone_number = request.form.get("phone_number")
    band_member = request.form.get("band_member")
    status = request.form.get("status")
    query = {"email": email}
    count = band_col.count_documents(query)
    if count == 0:
        query = {"band_name": band_name, "password": password,"confirm_password":confirm_password,"email": email, "address":address, "zipcode": zipcode, "phone_number": phone_number,"band_members_count":band_member,"status": "deactivated"}
        result = band_col.insert_one(query)
        band_id = result.inserted_id
        return render_template("band_members.html", band_id=band_id, band_members_count=band_member, int=int)
    else:
        return render_template("message.html", message="Duplicate Entry ")


@app.route("/band_members_actions", methods = ['post'])
def band_members_actions():
    band_id = request.form.get("band_id")
    band_members_count = request.form.get("band_members_count")
    band_members = []
    for i in range(int(band_members_count)):
        band_member = request.form.get("band_member"+str(i))
        band_members.append(band_member)
    query1 = {"_id": ObjectId(band_id)}
    query2 = {"$set": {"band_members": band_members}}
    band_col.update_one(query1, query2)
    return render_template("message.html", message="Band Registered Successfully")
@app.route("/band_login")
def band_login():
    return render_template("band_login.html")


@app.route("/band_login_action", methods=['post'])
def band_login_action():
    email = request.form.get("email")
    password = request.form.get("password")
    query = {"email": email, "password": password}
    count = band_col.count_documents(query)
    if count > 0:
        band = band_col.find_one(query)
        if band['status'] == "deactivated":
            return render_template("message.html",message="Not Verified")
        session['band_id'] = str(band['_id'])
        session['role'] = "band"
        return redirect("/band_home")
    else:
        return render_template("message.html",message="Invalid Login")


@app.route("/band_home")
def band_home():
    return render_template("band_home.html")


@app.route("/create_album")
def create_album():
    genres = genre_col.find()
    genres = list(genres)
    genre_id = request.args.get("genre_id")
    keyword = request.args.get("keyword")
    band_id = session['band_id']
    if genre_id == None:
        genre_id = ""
    if keyword == None:
        keyword =""
    keyword2 = re.compile(".*"+str(keyword)+".*",re.IGNORECASE)
    if genre_id!="":
        query = {"genre_id":ObjectId(genre_id),"album_name":keyword2, "band_id": ObjectId(band_id)}
    else:
        query = {"album_name":keyword2, "band_id": ObjectId(band_id)}
    albums = album_col.find(query)
    albums = list(albums)
    return render_template("create_album.html",genres=genres,albums=albums,get_genre_by_genre_id=get_genre_by_genre_id,get_band_by_band_id=get_band_by_band_id,keyword=keyword,genre_id=genre_id, str=str)


@app.route("/create_album_action",methods=['post'])
def create_album_action():
    album_name = request.form.get("album_name")
    band_id = session['band_id']
    genre_id = request.form.get("genre_id")
    poster = request.files.get("poster")
    path = POSTER_PATH + "/" + poster.filename
    poster.save(path)
    price = request.form.get("price")
    query = {"album_name": album_name, "band_id": ObjectId(band_id), "genre_id": ObjectId(genre_id), "poster": poster.filename, "price": price}
    album_col.insert_one(query)
    return render_template("message.html", message="Album Added  Successfully",get_genre_by_genre_id=get_genre_by_genre_id,get_band_by_band_id=get_band_by_band_id)


def get_genre_by_genre_id(genre_id):
    query = {"_id": genre_id}
    genre = genre_col.find_one(query)
    return genre


def get_band_by_band_id(band_id):
    query = {"_id": band_id}
    band = band_col.find_one(query)
    return band


@app.route("/songs")
def songs():
    album_id = request.args.get("album_id")
    query = {"_id":ObjectId(album_id)}
    album = album_col.find_one(query)
    query = {"album_id":ObjectId(album_id)}
    songs = song_col.find(query)
    songs = list(songs)
    return render_template("songs.html", album=album, album_id=album_id,get_album_by_album_id=get_album_by_album_id,songs=songs,str=str)


@app.route("/songs_action",methods=['post'])
def songs_action():
    song_name = request.form.get("song_name")
    song_poster = request.files.get("poster")
    is_demo_song = request.form.get("is_demo_song")
    path = SONG_POSTER_PATH  + "/" + song_poster.filename
    song_poster.save(path)
    song = request.files.get("song")
    path = SONG_PATH + "/" + song.filename
    song.save(path)
    duration = request.form.get("duration")
    album_id = request.form.get("album_id")
    status = request.form.get("status")
    price = request.form.get("price")
    query = {"song_name": song_name, "song_poster": song_poster.filename,"song":song.filename, "duration":duration,"album_id":ObjectId(album_id),"status": "not verified", "price": price, "is_demo_song":is_demo_song}
    song_col.insert_one(query)
    return render_template("message.html", message="Song Added Successfully",get_album_by_album_id=get_album_by_album_id)

def get_album_by_album_id(album_id):
    query = {"_id": album_id}
    album = album_col.find_one(query)
    return album


@app.route("/user_login")
def user_login():
    return render_template("user_login.html")


@app.route("/user_login_action",methods=['post'])
def user_login_action():
    email = request.form.get("email")
    password = request.form.get("password")
    query = {"email":email,"password":password}
    count = user_col.count_documents(query)
    if count > 0:
        user = user_col.find_one(query)
        session['user_id'] = str(user['_id'])
        session['role'] = "user"
        return redirect("/user_home")
    else:
        return render_template("message.html",message="Invalid Login")

@app.route("/user_registration")
def user_registration():
    return render_template("user_registration.html")


@app.route("/user_registration_action", methods=['post'])
def registration_action():
    user_name = request.form.get("user_name")
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    email = request.form.get("email")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")
    if password!= confirm_password:
        return render_template("message.html",message="Password didn't match")
    address = request.form.get("address")
    zipcode = request.form.get("zipcode")
    phone_number = request.form.get("phone_number")
    dob = request.form.get("dob")
    query = {"email": email}
    count = user_col.count_documents(query)
    print(email)
    if count == 0:
        query = {"user_name":user_name, "first_name":first_name,"last_name":last_name,"email":email,"password":password,"confirm_password":confirm_password,"address":address,"zipcode":zipcode,"phone_number":phone_number,"dob":dob}
        user_col.insert_one(query)
        return render_template("message.html",message="Register Successfully")
    else:
        return render_template("message.html",message="Duplicate Entry")


@app.route("/subscription")
def subscription():
    user_id = session['user_id']
    query = {"_id": ObjectId(user_id)}
    user = user_col.find_one(query)
    if 'enrollment_start_date' in user:
        today = datetime.datetime.now()
        if user['enrollment_start_date'] < today and user['enrollment_end_date'] >= today:
            return render_template("view_subscription.html", user=user)
    else:
        return render_template("subscription.html")



@app.route("/purchase")
def purchase():
    package_name = request.args.get("package_name")
    days = request.args.get("days")
    enrollment_start_date = datetime.datetime.now()
    enrollment_end_date = enrollment_start_date + datetime.timedelta(days=int(days))
    price = request.args.get("price")
    return render_template("purchase.html", package_name=package_name,days=days,enrollment_start_date=enrollment_start_date, enrollment_end_date=enrollment_end_date, price=price)

@app.route("/purchase_action", methods=['post'])
def purchase_action():
    user_id = session['user_id']
    package_name = request.form.get("package_name")
    days = request.form.get("days")
    card_type = request.form.get("card_type")
    card_number = request.form.get("card_number")
    cvv = request.form.get("cvv")
    expire_date = request.form.get("expire_date")
    price = request.form.get("price")
    enrollment_start_date = request.form.get("enrollment_start_date")
    enrollment_end_date = request.form.get("enrollment_end_date")
    enrollment_start_date = datetime.datetime.strptime(enrollment_start_date, '%Y-%m-%dT%H:%M')
    enrollment_end_date = datetime.datetime.strptime(enrollment_end_date, '%Y-%m-%dT%H:%M')
    query = {"card_type":card_type,"card_number":card_number,"cvv":cvv,"expire_date":expire_date,"price":price, "user_id": ObjectId(user_id), "date": datetime.datetime.now(), "status": "Payment Successfull"}
    payment_col.insert_one(query)
    query1 = {"_id": ObjectId(user_id)}
    query2 = {"$set":  {"user_id": ObjectId(user_id), "package_name": package_name, "days": days, "enrollment_start_date": enrollment_start_date, "enrollment_end_date": enrollment_end_date, "price": price}}
    user_col.update_one(query1, query2)
    return render_template("message.html",message="Subscription Purchased Successfully")



@app.route("/user_home")
def user_home():
    return render_template("user_home.html")


@app.route("/user_songs")
def user_songs():
    playlist_id = request.args.get("playlist_id")
    genre_id = request.args.get("genre_id")
    keyword = request.args.get("keyword")
    query_album = {}
    query_songs = {}
    playlist = None
    if genre_id == None:
        genre_id = ""
    if keyword == None:
        keyword = ""
    if playlist_id == None:
        playlist_id = ""
    if playlist_id != "":
        query = {"_id": ObjectId(playlist_id)}
        playlist = playlist_col.find_one(query)
        if 'albums_ids' in playlist:
            query_album = {"_id": {"$in":playlist['albums_ids']}}
        else:
            query_album = {"abc": "abc"}
        if 'song_ids' in playlist:
            query_songs = {"_id": {"$in":playlist['song_ids']}}
        else:
            query_songs = {"abc": "abc"}
    else:
        keyword2 = re.compile(".*"+str(keyword)+".*",re.IGNORECASE)
        if genre_id == "":
            query_album = {"album_name":keyword2}
        else:
            query_album = {"genre_id":ObjectId(genre_id),"album_name":keyword2}

        if genre_id == "":
            query_songs = {"song_name":keyword2}
        else:
            query = {"genre_id":ObjectId(genre_id)}
            albums2 = album_col.find(query)
            albums2 = list(albums2)
            album_ids = []
            for album in albums2:
                album_ids.append(album['_id'])
            query_songs = {"album_id":{"$in":album_ids},"song_name":keyword2}

    albums = album_col.find(query_album)
    albums = list(albums)
    genres = genre_col.find()
    genres = list(genres)
    songs = song_col.find(query_songs)
    songs = list(songs)
    print(keyword)
    return render_template("user_songs.html",albums=albums,songs=songs,genre_id=genre_id,keyword=keyword,str=str,genres= genres, get_genre_by_genre_id=get_genre_by_genre_id,get_band_by_band_id=get_band_by_band_id,get_album_by_album_id=get_album_by_album_id,get_songs_by_album_id=get_songs_by_album_id,playlist=playlist,is_user_brought_song=is_user_brought_song, is_subscribed=is_subscribed)

def is_user_brought_song(song_id):
    user_id = session['user_id']
    query = {"song_id": ObjectId(song_id),"user_id": ObjectId(user_id)}
    count = transaction_col.count_documents(query)
    if count > 0:
        return True
    else:
        query = {"_id": ObjectId(song_id)}
        song = song_col.find_one(query)
        query = {"album_id": song['album_id'], "user_id": ObjectId(user_id)}
        count = transaction_col.count_documents(query)
        if count > 0:
            return True
        else:
            return False
def get_songs_by_album_id(album_id):
    query = {"album_id":album_id}
    songs = song_col.find(query)
    songs = list(songs)
    return songs


@app.route("/playlist")
def playlist():
    user_id = session['user_id']
    query = {"user_id": ObjectId(user_id)}
    playlists = playlist_col.find(query)
    playlists = list(playlists)
    songs = song_col.find(query)
    songs = list(songs)
    return render_template("playlist.html",playlists=playlists,str=str,songs=songs)


@app.route("/playlist_action",methods=['post'])
def playlist_action():
    user_id = session['user_id']
    playlist_name = request.form.get("playlist_name")
    query = {"playlist_name": playlist_name, "user_id": ObjectId(user_id)}
    playlist_col.insert_one(query)
    return render_template("message.html",message="Playlist Added Successfully")


@app.route("/add_to_playlist")
def add_to_playlist():
    song_id = request.args.get("song_id")
    album_id = request.args.get("album_id")
    if album_id == None:
        album_id = ""
    if song_id == None:
        song_id = ""
    user_id = session['user_id']
    query = {"user_id": ObjectId(user_id)}
    print(query)
    playlists = playlist_col.find(query)
    playlists = list(playlists)
    print(playlists)
    return render_template("add_to_playlist.html",playlists=playlists,add_to_playlist=add_to_playlist,song_id=song_id,str=str, album_id=album_id)


@app.route("/add_to_playlist_action")
def add_to_playlist_action():
    playlist_id = request.args.get("playlist_id")
    song_id = request.args.get("song_id")
    album_id = request.args.get("album_id")
    if album_id == "":
        query = {"_id": ObjectId(playlist_id), "song_ids":ObjectId(song_id)}
        count = playlist_col.count_documents(query)
        if count > 0:
            return render_template("message.html",message="Song Already Added")
        query = {"_id": ObjectId(playlist_id)}
        query2 = {"$push": {"song_ids": ObjectId(song_id)}}
        playlist_col.update_one(query, query2)
        return render_template("message.html", message="Song Added To Favorite Successfully")

    if song_id == "":
        query = {"_id": ObjectId(playlist_id), "albums_ids":ObjectId(album_id)}
        count = playlist_col.count_documents(query)
        if count > 0:
            return render_template("message.html",message="Album Already Added")
        query = {"_id": ObjectId(playlist_id)}
        query2 = {"$push": {"albums_ids": ObjectId(album_id)}}
        playlist_col.update_one(query, query2)
        return render_template("message.html", message="Album Added To Favorite Successfully")

@app.route("/buy")
def buy():
    song_id = request.args.get("song_id")
    album_id = request.args.get("album_id")
    playlist_id = request.args.get("playlist_id")
    if song_id ==None:
        song_id = ""
    if album_id ==None:
        album_id = ""
    if playlist_id ==None:
        playlist_id = ""
    song = None
    album = None
    playlist = None
    playlist_price = 0
    if song_id != '':
        query = {"_id":ObjectId(song_id)}
        song = song_col.find_one(query)
    if album_id != '':
        query = {"_id": ObjectId(album_id)}
        album = album_col.find_one(query)
    if playlist_id != '':
        user_id = session["user_id"]
        query = {"_id": ObjectId(playlist_id)}
        playlist = playlist_col.find_one(query)
        print(playlist_id)
        if 'song_ids' in playlist:
            for song_id2 in playlist['song_ids']:
                query = {"_id": song_id2}
                song = song_col.find_one(query)
                query = {"user_id": ObjectId(user_id), "song_id": song_id2}
                count = transaction_col.count_documents(query)
                if count == 0:
                    playlist_price = playlist_price + int(song['price'])
        if 'albums_ids' in playlist:
            for albums_id2 in playlist['albums_ids']:
                query = {"_id": albums_id2}
                album = album_col.find_one(query)
                query = {"user_id": ObjectId(user_id), "album_id": albums_id2}
                count = transaction_col.count_documents(query)
                if count == 0:
                    playlist_price = playlist_price + int(album['price'])
    return render_template("buy.html", song_id=song_id,song=song,album_id=album_id,album=album,playlist_id=playlist_id,playlist=playlist,playlist_price=playlist_price,str=str,int=int)


@app.route("/buy_action",methods=['post'])
def buy_action():
    song_id = request.form.get("song_id")
    album_id = request.form.get("album_id")
    playlist_id = request.form.get("playlist_id")
    card_type = request.form.get("card_type")
    card_number = request.form.get("card_number")
    cvv = request.form.get("cvv")
    expire_date = request.form.get("expire_date")
    price = request.form.get("price")
    price = int(price)
    user_id = session['user_id']
    if song_id != "":
        query = {"user_id": ObjectId(user_id), "date": datetime.datetime.now(), "song_id": ObjectId(song_id)}
        result = transaction_col.insert_one(query)
        transaction_id = result.inserted_id
        admin_price = price * 2 / 100
        band_price = price * 98 / 100
        query = {"admin_price": admin_price, "band_price": band_price, "card_type": card_type,
                 "card_number": card_number, "cvv": cvv, "expire_date": expire_date, "date": datetime.datetime.now(),
                 "status": "Transaction Successful", "transaction_id":transaction_id, "user_id": ObjectId(user_id)}
        payment_col.insert_one(query)
    elif album_id!= "":
        query = {"user_id": ObjectId(user_id), "date": datetime.datetime.now(), "album_id": ObjectId(album_id)}
        result = transaction_col.insert_one(query)
        transaction_id = result.inserted_id
        admin_price = price * 2 / 100
        band_price = price * 98 / 100
        query = {"admin_price": admin_price, "band_price": band_price, "card_type": card_type,
                 "card_number": card_number, "cvv": cvv, "expire_date": expire_date, "date": datetime.datetime.now(),
                 "status": "Transaction Successful", "transaction_id":transaction_id, "user_id": ObjectId(user_id)}
        payment_col.insert_one(query)
    elif playlist_id != "":
        query = {"_id": ObjectId(playlist_id)}
        playlist = playlist_col.find_one(query)
        if 'song_ids' in playlist:
            for song_id in playlist['song_ids']:
                query = {"user_id": ObjectId(user_id), "song_id": song_id}
                count = transaction_col.count_documents(query)
                if count == 0:
                    query = {"user_id": ObjectId(user_id), "date": datetime.datetime.now(), "song_id": song_id}
                    result = transaction_col.insert_one(query)
                    transaction_id = result.inserted_id
                    query = {"_id": song_id}
                    song = song_col.find_one(query)
                    admin_price = int(song['price']) * 2 / 100
                    band_price = int(song['price']) * 98 / 100
                    query = {"admin_price": admin_price, "band_price": band_price, "card_type": card_type,
                             "card_number": card_number, "cvv": cvv, "expire_date": expire_date,
                             "date": datetime.datetime.now(),
                             "status": "Transaction Successful", "transaction_id":transaction_id, "user_id": ObjectId(user_id)}
                    payment_col.insert_one(query)
        if 'albums_ids' in playlist:
            for album_id in playlist['albums_ids']:
                query = {"user_id": ObjectId(user_id), "album_id": album_id}
                count = transaction_col.count_documents(query)
                if count == 0:
                    query = {"user_id": ObjectId(user_id), "date": datetime.datetime.now(), "album_id": album_id}
                    result = transaction_col.insert_one(query)
                    transaction_id = result.inserted_id
                    query = {"_id": album_id}
                    album = album_col.find_one(query)
                    admin_price = int(album['price']) * 2 / 100
                    band_price = int(album['price']) * 98 / 100
                    query = {"admin_price": admin_price, "band_price": band_price, "card_type": card_type,
                             "card_number": card_number, "cvv": cvv, "expire_date": expire_date,
                             "date": datetime.datetime.now(),
                             "status": "Transaction Successful", "transaction_id": transaction_id, "user_id": ObjectId(user_id)}
                    payment_col.insert_one(query)
    return render_template("message.html", message ="Your Transaction is Successful")


@app.route("/payment")
def payment():
    if session["role"] == 'admin':
        band_id = request.args.get("band_id")
        query = {"band_id": ObjectId(band_id)}
        albums = album_col.find(query)
        album_ids = []
        for album in albums:
            album_ids.append(album['_id'])
        query = {"album_id": {"$in": album_ids}}
        songs = song_col.find(query)
        songs = list(songs)
        song_ids = []
        for song in songs:
            song_ids.append(song['_id'])
        query = {"song_id": {"$in": song_ids}}
        transactions = transaction_col.find(query)
        transactions = list(transactions)
        transaction_ids = []
        print(transactions)
        for transaction in transactions:
            transaction_ids.append(transaction['_id'])
        query = {"album_id": {"$in": album_ids}}
        transactions = transaction_col.find(query)
        for transaction in transactions:
            transaction_ids.append(transaction['_id'])
        query = {"transaction_id": {"$in": transaction_ids}}
    elif session['role'] == 'user':
        user_id = session['user_id']
        query = {"user_id": ObjectId(user_id)}
    elif session['role'] == 'band':
        song_id = request.args.get("song_id")
        album_id = request.args.get("album_id")
        if song_id == None and album_id == None:
            band_id = session['band_id']
            query = {"band_id":ObjectId(band_id)}
            albums = album_col.find(query)
            album_ids = []
            for album in albums:
                album_ids.append(album['_id'])
            query = {"album_id": {"$in": album_ids}}
            songs = song_col.find(query)
            song_ids = []
            for song in songs:
                song_ids.append(song['_id'])
            query = {"song_id": {"$in":song_ids}}
            transactions = transaction_col.find(query)
            transaction_ids = []
            for transaction in transactions:
                transaction_ids.append(transaction['_id'])
            query = {"album_id": {"$in": album_ids}}
            transactions = transaction_col.find(query)
            for transaction in transactions:
                transaction_ids.append(transaction['_id'])
            query = {"transaction_id": {"$in": transaction_ids}}

        elif song_id != None:
            query = {"song_id": ObjectId(song_id)}
            transactions = transaction_col.find(query)
            transaction_ids = []
            for transaction in transactions:
                transaction_ids.append(transaction['_id'])
            query = {"transaction_id": {"$in": transaction_ids}}
        elif album_id != None:
            query = {"album_id": ObjectId(album_id)}
            transactions = transaction_col.find(query)
            transaction_ids = []
            for transaction in transactions:
                transaction_ids.append(transaction['_id'])
            query = {"transaction_id": {"$in": transaction_ids}}
    payments = payment_col.find(query)
    payments = list(payments)
    return render_template("payment.html",payments=payments,get_users_by_user_id=get_users_by_user_id)

def get_users_by_user_id(user_id):
    query = {"_id": user_id}
    user = user_col.find_one(query)
    return user

@app.route("/remove_playlist")
def remove_playlist():
    song_id = request.args.get("song_id")
    album_id = request.args.get("album_id")
    playlist_id = request.args.get("playlist_id")
    print(playlist_id)
    if song_id != None:
        query = {"_id": ObjectId(playlist_id)}
        print(query)
        query2 = {"$pull": {"song_ids": ObjectId(song_id)}}
        result = playlist_col.update_one(query, query2)
        print(result.matched_count)
        return render_template("message.html",message="Song Removed")
    if album_id != None:
        query = {"_id":ObjectId(playlist_id)}
        query2 = {"$pull":{"albums_ids":ObjectId(album_id)}}
        playlist_col.update_one(query,query2)
        return render_template("message.html",message="Album Removed")

def is_subscribed():
    user_id = session['user_id']
    query = {"_id": ObjectId(user_id)}
    user = user_col.find_one(query)
    if 'enrollment_start_date' in user:
        today = datetime.datetime.now()
        if user['enrollment_start_date'] < today and user['enrollment_end_date'] >= today:
            return True
        else:
            return False
    else:
        return False

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

app.run(debug=True)
