from builtins import Exception
import os

from django.shortcuts import render
from django.http import HttpResponse
from django.contrib import messages
from django.conf import settings

from user.forms import *
from user.models import *
from manager.models import *
from user.ranking import compute_weight, search_documents, clean_query


def index(request):
    return render(request,'index.html')

def logout(request):
    return render(request, "index.html")

def userlogin(request):
    return render(request,'user/userlogin.html')


def userregister(request):
    if request.method=='POST':
        form1=userForm(request.POST)
        if form1.is_valid():
            form1.save()
            print("succesfully saved the data")
            return render(request, "user/userlogin.html")
            #return HttpResponse("registreration succesfully completed")
        else:
            print("form not valied")
            return HttpResponse("form not valied")
    else:
        form=userForm()
        return render(request,"user/userregister.html",{"form":form})


def userlogincheck(request):
    if request.method == 'POST':
        sname = request.POST.get('email')
        print(sname)
        spasswd = request.POST.get('upasswd')
        print(spasswd)
        try:
            check = userModel.objects.get(email=sname,passwd=spasswd)
            # print('usid',usid,'pswd',pswd)
            print(check)
            # request.session['name'] = check.name
            # print("name",check.name)
            status = check.status
            print('status',status)
            if status == "Activated":
                request.session['email'] = check.email
                return render(request, 'user/userpage.html')
            else:
                messages.success(request, 'user is not activated')
                return render(request, 'user/userlogin.html')
        except Exception as e:
            print('Exception is ',str(e))
            pass
        messages.success(request,'Invalid name and password')
        return render(request,'user/userlogin.html')

def search(request):
    return render(request,'user/search.html')

def usersearchresult(request):
    filename = request.GET.get('filename')
    print("document type:",filename)
    check = uploadmodel.objects.filter(filename=filename)
    print(check)
    """for x in check:
        print(x.filename)
        print(x.filetype)
        print(x.id)"""
    object = check.filter(filename=filename)
    print("object:",object)
    return render(request, 'user/usersearchresult.html',{"object":object})

def weight(request):
    """The old 'Check' link: calculate the weight of one file and save it."""
    file = request.GET.get('file') or ''
    base = os.path.basename(file)
    path = os.path.join(settings.MEDIA_ROOT, 'files', 'pdfs', base)
    label_name = request.GET.get('filetype') or os.path.splitext(base)[0]
    s, rank, label = compute_weight(path)
    weightmodel.objects.update_or_create(
        file='files/pdfs/' + base,
        defaults={'filename': label_name, 'weight': s, 'rank': rank, 'label': label},
    )
    return render(request, "user/weight.html", {"dict": s})


def pagerank(request):
    return render(request, 'user/search.html')

def search1(request):
    return render(request,'user/search1.html')

def usersearchresult1(request):
    query = clean_query(request.GET.get('filename'))
    results = search_documents(query)
    return render(request, 'user/userdisplay.html', {
        "qs": results,
        "query": query,
        "indexed_count": weightmodel.objects.count(),
    })
