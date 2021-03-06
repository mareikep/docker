
from flask import session, jsonify, request, redirect, render_template, url_for, Markup, send_from_directory
from flask_user import login_required
from flask.ext.misaka import markdown

import os, re
import json

from urlparse import urlparse

from webrob.app_and_db import app, db
from webrob.user.knowrob_user import read_tutorial_page
from webrob.docker.docker_application import ensure_application_started
from webrob.docker import docker_interface

from utility import *

MAX_HISTORY_LINES = 50

@app.route('/knowrob/static/<path:filename>')
@login_required
def download_static(filename):
  return send_from_directory(os.path.join(app.root_path, "static"), filename)

@app.route('/knowrob/knowrob_data/<path:filename>')
@login_required
def download_logged_image(filename):
  return send_from_directory('/home/ros/knowrob_data/', filename)

@app.route('/knowrob/summary_data/<path:filename>')
@login_required
def download_summary_image(filename):
  # TODO migrate summary_data -> users own data container and use docker_interface to retrieve summary!
  return send_from_directory('/home/ros/summary_data/', filename)

@app.route('/knowrob/tutorials/')
@app.route('/knowrob/tutorials/<cat_id>/')
@app.route('/knowrob/tutorials/<cat_id>/<page>')
# @login_required
def tutorials(cat_id='getting_started', page=1):
    session['video'] = 0
    if not ensure_application_started('knowrob/hydro-knowrob-daemon'):
        return redirect(url_for('/knowrob/tutorials/'))
    
    error=""
    # determine hostname/IP we are currently using
    # (needed for accessing container)
    host_url = urlparse(request.host_url).hostname
    container_name = session['user_container_name'] # 'tutorials'
    show_south_pane = False
    readonly = True
    authentication = False

    tut = read_tutorial_page(cat_id, page)
    content = markdown(tut.text, fenced_code=True)

    # automatically add event handler for highlighting DOM elements
    tmp = re.findall('<em>(.*?)</em>', str(content))
    for t in tmp:
        if 'hl_' in t:
            text = t.split(' hl_')[0]
            idname = t.split(' hl_')[1]
            content = re.sub('<em>{} hl_{}</em>'.format(text, idname), '<em onmouseover="knowrob.highlight_element(&#39;{0}&#39;, &#39;id&#39;, true)" onmouseout="knowrob.highlight_element(&#39;{0}&#39;, &#39;id&#39;, false)">{1}</em>'.format(idname, text), str(content))
        elif 'hlc_' in t:
            text = t.split(' hlc_')[0]
            classname = t.split(' hlc_')[1]
            content = re.sub('<em>{} hlc_{}</em>'.format(text, classname), '<em onmouseover="knowrob.highlight_element(&#39;{0}&#39;, &#39;class&#39;, true)" onmouseout="knowrob.highlight_element(&#39;{0}&#39;, &#39;class&#39;, false)">{1}</em>'.format(classname, text), str(content))

    # automatically add "ask as query" links after code blocks
    content = re.sub('</code>(\s)?</pre>', "</code></pre><div class='show_code'><a href='#' class='show_code'>Ask as query</a></div>", str(content))
    content = Markup(content)

    # check whether there is another tutorial in this category
    nxt  = read_tutorial_page(cat_id, int(page)+1)
    prev = read_tutorial_page(cat_id, int(page)-1)

    return render_template('knowrob_tutorial.html', **locals())

@app.route('/knowrob/')
@app.route('/knowrob/hydro-knowrob-daemon')
@app.route('/knowrob/exp/<path:exp_path>')
@login_required
def knowrob(exp_path=None):
    session['video'] = 0
    if not ensure_application_started('knowrob/hydro-knowrob-daemon'):
        return redirect(url_for('user.logout'))
    
    error=""
    # determine hostname/IP we are currently using
    # (needed for accessing container)
    host_url = urlparse(request.host_url).hostname

    container_name = session['user_container_name']
    show_south_pane = True
    # Remember experiment selection
    if exp_path is not None: session['exp'] = exp_path
    # Select a query file
    exp_query_file = None
    if 'exp' in session:
        exp = session['exp']
        if exp is not None: exp_query_file = exp + '.json'
    # TODO: Allow to select html template using a experiment configuration file

    return render_template('knowrob_simple.html', **locals())

@app.route('/knowrob/video')
@app.route('/knowrob/video/exp/<path:exp_path>')
@login_required
def video(exp_path=None):
    session['video'] = 1
    if not ensure_application_started('knowrob/hydro-knowrob-daemon'):
        return redirect(url_for('user.logout'))
    
    error=""
    # determine hostname/IP we are currently using
    # (needed for accessing container)
    host_url = urlparse(request.host_url).hostname
    container_name = session['user_container_name']

    # Remember experiment selection
    if exp_path is not None: session['exp'] = exp_path
    # Select a query file
    exp_query_file = None
    if 'exp' in session:
        exp = session['exp']
        if exp is not None: exp_query_file = exp + '.json'
    
    return render_template('video.html', **locals())

@app.route('/knowrob/menu', methods=['POST'])
@app.route('/knowrob/hydro-knowrob-daemon/menu', methods=['POST'])
def menu():
    knowrobUrl = '/knowrob/'
    
    menu_left = [
        ('Knowledge Base',      knowrobUrl),
        ('Robot Memory Replay', knowrobUrl+'video'),
        ('Editor',              knowrobUrl+'editor')
    ]
    
    exp_selection = __exp_file__()
    if exp_selection is None: exp_selection = "Experiment"
    
    exp_choices_map =  {}
    for (submenu,exp) in __exp_list__():
        # Find exp url
        exp_url = knowrobUrl
        if __is_video__():
            exp_url += 'video/'
        exp_url += 'exp/'
        if len(submenu)>0:
            exp_url += submenu + '/'
        exp_url += exp
        
        menu = ''
        if len(submenu)>0:
            menu = submenu
        if not menu in exp_choices_map:
            exp_choices_map[menu] = []
        
        exp_choices_map[menu].append((exp, exp_url))
    
    exp_choices = []
    exp_map_keys = exp_choices_map.keys()
    exp_map_keys.sort()
    
    for key in exp_map_keys:
        if key == '': continue
        exp_choices_map[key].sort()
        exp_choices.append(('CHOICES', (key+' >>', exp_choices_map[key])))
    if '' in exp_map_keys:
        exp_choices_map[''].sort()
        exp_choices += exp_choices_map['']
    
    menu_right = [
        ('CHOICES', (exp_selection, exp_choices))
    ]
    
    return jsonify(menu_left=menu_left, menu_right=menu_right)

def __exp_menu_file__(f, category):
    if f.endswith(".json"):
        return (category, f[0:len(f)-len(".json")])
    else:
        return None
 
def __exp_list__():
    expList = []
    exp_root_path = os.path.join(app.root_path, "static/experiments/queries")
    
    for f0 in os.listdir(exp_root_path):
        exp_path = os.path.join(exp_root_path, f0)
        
        # Query file with submenu
        if os.path.isdir(exp_path):
            for f1 in os.listdir(exp_path):
                menu_entry = __exp_menu_file__(f1, f0)
                if menu_entry != None: expList.append(menu_entry)
        
        # Query file without submenu
        else:
            menu_entry = __exp_menu_file__(f0, '')
            if menu_entry != None: expList.append(menu_entry)
    
    return expList

def __exp_file__():
    if 'exp' in session:
        return session['exp']
    else:
        return None

def __is_video__():
    if 'video' in session:
        return session['video']
    else:
        return 0
    
@app.route('/knowrob/exp_set', methods=['POST'])
@login_required
def exp_set():
    expName = json.loads(request.data)['experimentName']
    session['exp'] = expName
    return jsonify(result=None)

@app.route('/knowrob/add_history_item', methods=['POST'])
@login_required
def add_history_item():
  query = json.loads(request.data)['query']
  hfile = get_history_file()
  # Remove newline characters
  query.replace("\n", " ")
  
  # Read history
  lines = []
  if os.path.isfile(hfile):
    f = open(hfile)
    lines = f.readlines()
    f.close()
  # Append the last query
  lines.append(query+".\n")
  # Remove old history items
  numLines = len(lines)
  lines = lines[max(0, numLines-MAX_HISTORY_LINES):numLines]
  
  with open(hfile, "w") as f:
    f.writelines(lines)
  
  return jsonify(result=None)

@app.route('/knowrob/get_history_item', methods=['POST'])
@login_required
def get_history_item():
  index = json.loads(request.data)['index']
  
  if index<0:
    return jsonify(item="", index=-1)
  
  hfile = get_history_file()
  if os.path.isfile(hfile):
    # Read file content
    f = open(hfile)
    lines = f.readlines()
    f.close()
    
    # Clamp index
    if index<0: index=0
    if index>=len(lines): index=len(lines)-1
    if index<0: return jsonify(item="", index=-1)
    
    item = lines[len(lines)-index-1]
    item = item[:len(item)-1]
    
    return jsonify(item=item, index=index)
  
  else:
    return jsonify(item="", index=-1)


def get_history_file():
  userDir = get_user_dir()
  return os.path.join(get_user_dir(), "query.history")
