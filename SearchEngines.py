import time
import requests
import os.path

from PIL import ImageFile
from selenium import webdriver
from urllib.request import Request, urlopen, urlretrieve
from hashlib import sha1

# Settings
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'
IMAGE_LOAD_SLEEP_TIME = 0.2
IMAGE_LOAD_RETRIES = 50 # max amount of retries with delay IMAGE_LOAD_SLEEP_TIME

SEARCH_ENGINES = {
    "Google" : {
        "search_url": "https://www.google.com/search?safe=off&site=&tbm=isch&source=hp&q={q}&oq={q}&gs_l=img",
        "image_resolution_divider": " × ",
        "selectors": {
            "load_more": "input.mye4qd",
            "thumbnail": "img.rg_i",   
            "image_resolution": "div.O1vY7 > span",                           

            "image": "img.n3VNCb", 
            "actual_resolution": "span.VSIspc",     
            "loading_progressbar": "div.k7O2sd",
            }
        },
    "DuckDuckGo" : {
        "search_url": "https://duckduckgo.com/?q={q}&iar=images&iax=images&ia=images",
        "image_resolution_divider": " × ",
        "selectors": {
            "thumbnail": "img.tile--img__img",    
            "image_resolution": "div.tile--img__dimensions > em",

            "image_link": "a.detail__media__img-link",
            "actual_resolution": "div.c-detail__filemeta",
            }
        }
    }

def getTrueImageResolution(url):
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
    response = requests.head(url, verify=False)
    return response.headers['content-type']

def downloadImage(url, saveFilePath):
    response = requests.get(url, headers={'User-Agent': USER_AGENT}, allow_redirects=True, verify=False)
    open(saveFilePath, 'wb').write(response.content)

def getStringHash(strToHash):
    return sha1(strToHash.encode('utf-8')).hexdigest()

def getImageFileName(imgUrl, imgContentType):
    return getStringHash(imgUrl) + "." + imgContentType.replace("image/", "")

def isResolutionValid(img_resolution, min_resolution, max_resolution):
    if not img_resolution:
        return False

    # Check if image resolution bigger than minResolution
    if (img_resolution[0] < min_resolution[0]) or (img_resolution[1] < min_resolution[1]):
        return False

    # Check if image resolution smaller than maxResolution
    if (img_resolution[0] > max_resolution[0]) or (img_resolution[1] > max_resolution[1]):
        return False        

    return True

def isContentTypeValid(img_contentType, valid_contentTypes):
    if not img_contentType:
        return False

    return img_contentType in valid_contentTypes

def isImageValid(img_url, img_resolution, min_resolution, max_resolution, img_contentType, valid_contentTypes):
    if (not img_url):
        return False
   
    if not isContentTypeValid(img_contentType, valid_contentTypes):
        return False

    if not isResolutionValid(img_resolution, min_resolution, max_resolution):
        return False

    return True

def tryDownloadImage(img_url, search_engine, img_resolution, min_resolution, max_resolution, valid_contentTypes, save_dir):
    try:
        img_contentType = getImageContentType(img_url)

        if isImageValid(img_url, img_resolution, min_resolution, max_resolution, img_contentType, valid_contentTypes):
            image_fileName = getImageFileName(img_url, img_contentType)
            save_filePath = os.path.join(save_dir, image_fileName)

            if os.path.exists(save_filePath):
                return False

            # check resolution of image by url (because google can display cached resolution, but link can be new)
            if not isResolutionValid(getTrueImageResolution(img_url), min_resolution, max_resolution):
                return False

            downloadImage(img_url, save_filePath)
            print(img_url + " $$ " + image_fileName)
            return True 
    except Exception as ex:        
        print("tryDownloadImage: ", ex)

    return False

# Returns True if image was downloaded
def processImageGoogle(wd, search_engine, min_resolution, max_resolution, valid_contentTypes, save_dir):
    try:
        # wait for load of image IMAGE_LOAD_RETRIES * IMAGE_LOAD_SLEEP_TIME seconds
        # if image will not load, preview will be downloaded
        for _ in range(IMAGE_LOAD_RETRIES):
            time.sleep(IMAGE_LOAD_SLEEP_TIME)
            loading_progressbars = wd.find_elements_by_css_selector(SEARCH_ENGINES[search_engine]["selectors"]["loading_progressbar"])

            for loading_progressbar in loading_progressbars:
                # at least one progress bar visible
                if not loading_progressbar.get_attribute("style"):
                    break
            else:    
                # all loading progressbars are hidden   
                break                                          

        # actual_images would be array with 3 elements (prev, current, next, but random order)
        actual_images = wd.find_elements_by_css_selector(SEARCH_ENGINES[search_engine]["selectors"]["image"]) 
        actual_resolutions = wd.find_elements_by_css_selector(SEARCH_ENGINES[search_engine]["selectors"]["actual_resolution"])               
        
        if len(actual_images) != len(actual_resolutions):
            print("ERROR: Length of actual_images not equal to length of actual_resolutions")
            return False

        for actual_image, actual_resolution in zip(actual_images, actual_resolutions):          
            img_url = actual_image.get_attribute("src")

            if img_url.startswith("data:"):
                # print("Skip data: image")
                continue

            resolution = actual_resolution.get_attribute("innerHTML").split(SEARCH_ENGINES[search_engine]["image_resolution_divider"])
            resolution[0], resolution[1] = int(resolution[0]), int(resolution[1])

            if tryDownloadImage(img_url, search_engine, resolution, min_resolution, max_resolution, valid_contentTypes, save_dir):
                return True
    except Exception as ex:
        print("processImageGoogle: ", ex)   

    return False

# Returns True if image was downloaded
def processImageDuckDuckGo(wd, search_engine, min_resolution, max_resolution, valid_contentTypes, save_dir):   
    try:
        time.sleep(IMAGE_LOAD_SLEEP_TIME)
  
        # actual_images would be array with 3 elements (prev, current, next, but random order)
        actual_image_links = wd.find_elements_by_css_selector(SEARCH_ENGINES[search_engine]["selectors"]["image_link"]) 
        actual_resolutions = wd.find_elements_by_css_selector(SEARCH_ENGINES[search_engine]["selectors"]["actual_resolution"])               
        
        if len(actual_image_links) != len(actual_resolutions):
            print("ERROR: Length of actual_image_links not equal to length of actual_resolutions")
            return False

        for actual_image_link, actual_resolution in zip(actual_image_links, actual_resolutions):              
            img_url = actual_image_link.get_attribute("href")

            if img_url.startswith("data:"):
                continue

            resolution = actual_resolution.get_attribute("innerHTML").split(SEARCH_ENGINES[search_engine]["image_resolution_divider"])
            resolution[0], resolution[1] = int(resolution[0]), int(resolution[1])

            if tryDownloadImage(img_url, search_engine, resolution, min_resolution, max_resolution, valid_contentTypes, save_dir):
                return True
    except Exception as ex:
        print("processImageDuckDuckGo: ", ex)   

    return False