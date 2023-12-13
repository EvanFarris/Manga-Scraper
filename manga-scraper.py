import csv
import os
import re
import requests
import time
from bs4 import BeautifulSoup

series_dict = {}
nickname_dict = {}

def parse_url(url):
    r = re.compile('/+')
    split_url = r.split(url)
    if len(url) == 0:
        return None

    r = re.compile('^https?:$')
    if r.match(split_url[0]):
        split_url.pop(0)
    
    if len(split_url) <= 1:
        return ("Error: Invalid url submitted")
    
    r = re.compile('^[^.].+[.].+[^.]$') #Regex to make sure there is a domain name, and that the domain does not start or end with a period.
    if not r.match(split_url[0]):
        return ("Error: Invalid domain name")
    series_identifier = split_url[len(split_url) - 1]
    split_url.pop()
    domain = split_url[0]
    split_url.pop(0)
    
    if domain.startswith("www."):
        domain = domain[4:]
    series_prefix = "/".join(split_url)

    return (domain, series_prefix , series_identifier)

def getSeriesPage(domain, series_prefix, series_identifier):
    session = requests.Session()
    headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
           'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
           'Accept-Language':'en-US'}
    
    url = 'https://' + domain + '/'
    if len(series_prefix) > 0:
        url += series_prefix + '/' 
    url += series_identifier
    try:
        req = session.get(url, headers=headers)
    except:
        print("Error fetching URL")
        return None
        
    bs = BeautifulSoup(req.text, 'html.parser')
    if bs.title.get_text() == "404 Not Found":
        print("404 Not Found | series not found in domain")
        return None
    
    return bs

def getChapterList(bs):
    result = []
    bs_list = bs.find('ul',class_="row-content-chapter")
    if bs_list is None:
        bs_list = bs.find('div','chapter-list').find_all('div',class_="row")
        for row in bs_list:
            spans = row.find_all('span')
            link = spans[0].a.attrs['href']
            title = spans[0].a.get_text().encode("ascii","ignore").decode()
            upload_date = spans[2].get_text()
            result.append((title, upload_date, link))
    else:
        for li in bs_list.find_all('li'):
            link = li.a.attrs['href']
            title = li.a.get_text().encode("ascii","ignore").decode()
            upload_date = li.find(class_='chapter-time').get_text()
            result.append((title, upload_date, link))
    return result

def writeBS(path, mode, data):
    if len(data) == 0:
        return
    with open(path, mode, newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter='\t')
        data.reverse()
        for row in data:
            writer.writerow([row[0], row[1], row[2]])

def track_series(series_info):
    # series_info -> (domain, series_prefix, series_identifier)
    domain = series_info[0]
    series_prefix = series_info[1]
    series_identifier = series_info[2]
    
    bs = getSeriesPage(domain, series_prefix, series_identifier)
    if bs == None:
        return None
    
    try:
        series_title = bs.find('h1').get_text()
        print(series_title)
    except:
        print("Web page found is either not a series page, or has a different page structure...")
        return None

    while True:
        series_nickname = input("Enter a nickname for the series\n")
        if not series_nickname:
            continue
        if series_nickname and nickname_dict.get(series_nickname) is None:
            break
        else:
            print("Nickname already used...\n")
    progress = "-1"
    track_progress = input("Do you want to track your progress? (y/n)\n")
    if "y" in track_progress or "Y" in track_progress:
        progress = input("Enter the chapter you are currently on. Ex: If the latest chapter you read was 'VOL.23 CHAPTER 68.2: THE S... ' you would enter: 68.2\n")

    series_d_entry = f'{domain}--{series_identifier}'
    #Update dictionaries
    nickname_dict[series_nickname] = series_d_entry
    ##Probably want to refine what series_dict stores in the future - reduce redundancy? possibly make a domain dictionary
    series_dict[series_d_entry] = (series_title, domain, series_prefix, series_identifier, progress)
    
    #Store info to disk
    if not os.path.exists('./data'):
        os.mkdir('./data')

    bs_list = getChapterList(bs)
    writeBS(f'./data/{series_d_entry}.csv', 'w', bs_list)

    with open("./data/series_info.csv",'a', newline = '') as csv_file:
        writer = csv.writer(csv_file, delimiter='\t')
        writer.writerow([series_title, domain, series_prefix, series_identifier, progress])
    with open("./data/nickname_info.csv",'a', newline = '') as csv_file:
        writer = csv.writer(csv_file, delimiter='\t')
        writer.writerow([series_nickname, series_d_entry])
    
    return None
    
    
def check_all():
    #Check every series, if any new chapters found, update file, only display series name, new chapters, and links to new chapters
    if len(series_dict) == 0:
        print("No series are being tracked.")
    for nickname in nickname_dict.keys():
        check_series(nickname)
        time.sleep(1)
    
def check_series(nickname = None):
    #Check for new chapters, if any new chapters: update file, show list of new chapters and links to new chapters
    #Show number of chapters, unread chapters
    if len(series_dict) == 0:
        print("No series are being tracked.")
        return

    if not nickname or (nickname and nickname_dict.get(nickname) == None):
        while True:
            nickname = input("Enter nickname for the series, or nothing to return.\n")
            if nickname == "":
                return
            if nickname_dict.get(nickname) is not None:
                break
    
    si = series_dict[nickname_dict[nickname]]
    title = si[0]
    bs = getSeriesPage(si[1],si[2],si[3])
    series_location = f'./data/{si[1]}--{si[3]}.csv'
    if not os.path.isfile(series_location):
        return None;
    with open(series_location,'r') as csv_file:
        reader = csv.reader(csv_file, delimiter="\t")
        chapters_stored = 0
        for row in reader:
            chapters_stored += 1
    bs_list = getChapterList(bs)
    #May encounter problems if chapters are reuploaded, or if fake chapters added
    difference = len(bs_list) - chapters_stored
    if difference >= 0:
        letter_s = "s" * (difference != 1)
        print(f'{title} - {difference} new chapter{letter_s}, {len(bs_list)} total\n')
        counter = difference - 1
        while counter > 0:
            print(f'\t{bs_list[counter].a.get_text()}\n')
            counter -= 1
        bs_list = bs_list[:difference]
        open_mode = 'a+'
    else:
        print(f'Some chapters were deleted on the website.')
        open_mode = 'w+'
    
    if difference:
        writeBS(series_location, open_mode, bs_list)
    
def add_series():
    #In a loop
        #Check if series exists already
        #If not, print to console
        #Add series if not present
        #Set how many chapters user has read(tracking)
    while True:
        url = input('Submit the link to the series to track. Enter nothing to return to the main menu.\n')
        series = parse_url(url)
        if series == None:
            break
        elif len(series) == 1:
            print(series[0])
        elif series and f'{series[0]}--{series[2]}' not in series_dict:
            track_series(series)        
        else:
            print("Series already being tracked.\n")

def list_series():
    #Show Title of every list found, Total # of chapters, #of chapters read|unread
    if len(series_dict) == 0:
        print("No series are being tracked.")
        return
    
    nicknames = sorted(nickname_dict.keys())
    print("Nickname | Series Title\n")
    for nickname in nicknames:
        title = series_dict[nickname_dict[nickname]][0]
        print(f'{nickname} | {title}\n')

def delete_series():
    #stop tracking series from check_all, ask to confirm deletion from disk
    print("To be implemented in the future\n")

def load_dictionary(csv_file_name):
    csv_file_name = "./data/" + csv_file_name
    if not os.path.isfile(csv_file_name):
        return;
        
    with open(csv_file_name, "r") as csvfile:
        csv_reader = csv.reader(csvfile, delimiter='\t')
        if csv_reader:
            if csv_file_name == "./data/series_info.csv":
                for row in csv_reader:
                    series_dict[f'{row[1]}--{row[3]}'] = (row[0], row[1], row[2], row[3], row[4])
            elif csv_file_name == "./data/nickname_info.csv":
                for row in csv_reader:
                    nickname_dict[row[0]] = row[1]
    
load_dictionary("series_info.csv")
load_dictionary("nickname_info.csv")

while True:
    user_input = input('Choose an option:\n1: Check every series for new chapters\n2: See all chapters in a particular series\n3: Track a new series\n4: List all series\ndelete: Delete a series\nquit to exit\n\n')
    
    match user_input:
        case '1':
            print('\n--------------------------------------------------\n')
            check_all()
            print('\n--------------------------------------------------\n')
        case '2':
            print('\n--------------------------------------------------\n')
            check_series()
            print('\n--------------------------------------------------\n')
        case '3':
            print('\n--------------------------------------------------\n')
            add_series()
            print('\n--------------------------------------------------\n')
        case '4':
            print('\n--------------------------------------------------\n')
            list_series()
            print('\n--------------------------------------------------\n')
        case 'delete':
            print('\n--------------------------------------------------\n')
            delete_series()
            print('\n--------------------------------------------------\n')
        case 'quit':
            break
        case _:
            print('')
