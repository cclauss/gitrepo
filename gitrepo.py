# coding: utf-8

import clipboard, console, requests, ui, urlparse, zipfile
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO  import StringIO

class Delegate (object):
    def __init__(self):
        self.selected_item = None
    
    def tableview_did_select(self, tableview, section, row):
        self.selected_item = tableview.data_source.items[row]
        tableview.superview.close()

repolink    = "https://github.com/{}/{}/archive/master.zip"
browselink  = "https://api.github.com/users/{}/repos"
releaselink = "https://api.github.com/repos/{}/{}/releases"

def error_alert(msg="General error"):
    console.alert("Error", msg, "OK", hide_cancel_button=True)

@ui.in_background
def save_zip(data, name, unzip):
    if unzip:
        io = StringIO(data)
        with zipfile.ZipFile(io) as zp:
            zp.extractall()
    else:
        with open(name + ".zip", "wb") as zp:
            zp.write(data)

@ui.in_background
def download_repo(username, repo, unzip):
    url = repolink.format(username, repo)
    try:
        save_zip(requests.get(url).content, repo, unzip)
    except Exception as err:
        return error_alert("Error downloading repo: {}".format(err))
    console.hud_alert("Done!")

@ui.in_background
def download_release(username, repo, unzip):
    url = releaselink.format(username, repo)
    data = requests.get(url).json()
    if not data:
        return error_alert("This repo has no releases: " + url)
    elif "message" in data and data["message"] == "Not Found":
        return error_alert("Repo '{}' not found".format(repo))
    vers = sorted([i["tag_name"] for i in data])
    rview = data_view("release", vers)
    rview.present("sheet")
    rview.wait_modal()
    tapped_text = rview["rtable"].delegate.selected_item
    if tapped_text:
        for d in data:
            if d["tag_name"] == tapped_text:
                zipurl = d["zipball_url"]
                save_zip(requests.get(zipurl).content, tapped_text, unzip)
                return console.hud_alert("Done!")

@ui.in_background
def gitdownload(button):
    isrelease = view["sgcontrol"].selected_index
    username  = view["username"].text = view["username"].text.strip()
    reponame  = view["reponame"].text = view["reponame"].text.strip()
    unzip     = view["dounzip"].value
    if not username:
        return error_alert("Please enter username")
    if not reponame:
        return error_alert("Please enter repo name")
    console.show_activity()
    if isrelease:
        download_release(username, reponame, unzip)
    else:
        download_repo(username, reponame, unzip)
    console.hide_activity()

@ui.in_background
def gitbrowse(sender):
    username = view["username"].text = view["username"].text.strip()
    if not username:
        return error_alert("Please enter username")
    url = browselink.format(username)
    try:
        data = requests.get(url).json()  # normally returns a list of dicts
    except requests.HTTPError as err:
        return console.alert("User '{}' not found".format(username))
    except Exception as err:
        return console.alert("Error downloading metadata: {}".format(err))
    if isinstance(data, dict) and data["message"] == "Not Found":
        return console.alert("User '{}' not found".format(username))
    repos = sorted([i["name"] for i in data])
    rview = data_view("repo", repos)
    rview.present("sheet")
    rview.wait_modal()
    tapped_text = rview["rtable"].delegate.selected_item
    if tapped_text:
        view["reponame"].text = tapped_text

def data_view(name, data):
    rview = ui.View(name="Choose a " + name)
    table = ui.TableView()
    table.name = "rtable"
    table.flex = "WH"
    table.data_source = ui.ListDataSource(data)
    table.data_source.delete_enabled = False
    table.delegate = Delegate()
    rview.add_subview(table)
    return rview

view = ui.load_view('gitrepo')
for name in 'username reponame'.split():
    view[name].autocapitalization_type = ui.AUTOCAPITALIZE_NONE
parse = urlparse.urlparse(clipboard.get().strip())
if parse.scheme:
    path = [i for i in parse.path.split("/") if i]
    if len(path) >= 2:
        view["username"].text, view["reponame"].text = path[:2]
view.present('popover')
