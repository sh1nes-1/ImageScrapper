import time
import requests
import os.path

from PIL import ImageFile
from selenium import webdriver
from urllib.request import Request, urlopen, urlretrieve
from hashlib import sha1

# Settings
USER_AGENT = 'Mozilla/5.0'
IMAGE_LOAD_SLEEP_TIME = 0.2
IMAGE_LOAD_RETRIES = 50 # max amount of retries with delay IMAGE_LOAD_SLEEP_TIME

SEARCH_ENGINES = {
    "Google" : {
        # Common
        "search_url": "https://www.google.com/search?safe=off&site=&tbm=isch&source=hp&q={q}&oq={q}&gs_l=img",
        "thumbnail_css_selector": "img.rg_i",
        "load_more_css_selector": "input.mye4qd",

        # Specific
        "image_css_selector": "img.n3VNCb",        
        "loading_progressbar_selector": "div.k7O2sd"
        }
    }

def getImageResolution(url):
    file = urlopen(Request(url, headers={'User-Agent': USER_AGENT}))
    p = ImageFile.Parser()

    while True:
        data = file.read(1024)
        if not data:
            break
        p.feed(data)
        if p.image:
            return p.image.size

    file.close()
    return None

def getImageContentType(url):
    response = requests.head(url)
    return response.headers['content-type']

# Returns
# (resolution, contentType): if success
# (None, None): if can't get at least one
def getImageResolutionAndContentType(imgUrl):
    try:
        imgResolution = getImageResolution(imgUrl)
        imgContentType = getImageContentType(imgUrl)
        return (imgResolution, imgContentType)
    except Exception as ex:
        print(ex)
        return (None, None)

def isImageValid(imgUrl, imageResolution, imgContentType, minResolution, maxResolution, imageContentTypes):
    # Check if img parameters is valid
    if (not imgUrl) or (not imgContentType) or (not imageResolution):
        #print("Can't parse info")
        return False
    
    # Check if image content type is valid
    if not (imgContentType in imageContentTypes):
        #print("Invalid image ext")
        return False

    # Check if image resolution bigger than minResolution
    if (imageResolution[0] < minResolution[0]) or (imageResolution[1] < minResolution[1]):
        #print("Min res")
        return False

    # Check if image resolution smaller than maxResolution
    if (imageResolution[0] > maxResolution[0]) or (imageResolution[1] > maxResolution[1]):
        #print("Max res")
        return False

    return True

def downloadImage(url, saveFilePath):
    try:
        response = requests.get(url, headers={'User-Agent': USER_AGENT}, allow_redirects=True)
        open(saveFilePath, 'wb').write(response.content)
        return True
    except Exception as ex:
        print(ex)
        return False

def getStringHash(strToHash):
    return sha1(strToHash.encode('utf-8')).hexdigest()

def getImageFileName(imgUrl, imgContentType):
    return getStringHash(imgUrl) + "." + imgContentType.replace("image/", "")

# Returns True if image was downloaded
def processImageGoogle(wd, img, searchEngine, minResolution, maxResolution, imageContentTypes, saveDir):
    # try to click every thumbnail such that we can get the real image behind it
    try:
        img.click()                
    except Exception:
        return None                     

    # wait for load of image IMAGE_LOAD_RETRIES * IMAGE_LOAD_SLEEP_TIME seconds
    # if image will not load, preview will be downloaded
    for _ in range(IMAGE_LOAD_RETRIES):
        time.sleep(IMAGE_LOAD_SLEEP_TIME)
        loading_progressbars = wd.find_elements_by_css_selector(SEARCH_ENGINES[searchEngine]["loading_progressbar_selector"])

        for loading_progressbar in loading_progressbars:
            # at least one progress bar visible
            if not loading_progressbar.get_attribute("style"):
                break
        else:    
            # all loading progressbars are hidden   
            break                                          

    # extract image urls    
    actual_images = wd.find_elements_by_css_selector(SEARCH_ENGINES[searchEngine]["image_css_selector"])                

    for actual_image in actual_images:                
        imgUrl = actual_image.get_attribute("src")

        if imgUrl.startswith("data:"):
            continue

        imgResolution, imgContentType = getImageResolutionAndContentType(imgUrl)

        if isImageValid(imgUrl, imgResolution, imgContentType, minResolution, maxResolution, imageContentTypes):
            imageFileName = getImageFileName(imgUrl, imgContentType)
            saveFilePath = os.path.join(saveDir, imageFileName)

            if os.path.exists(saveFilePath):
                continue

            if downloadImage(imgUrl, saveFilePath):
                print(imgUrl + " $$ " + imageFileName)
                return True    