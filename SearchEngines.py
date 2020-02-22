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
            "loading_progressbar": "div.k7O2sd"
            }
        },
    "DuckDuckGo" : {
        "search_url": "https://duckduckgo.com/?q={q}&iar=images&iax=images&ia=images",
        "thumbnail_css_selector": "img.tile--img__img",    
        "image_link_selector": "a.detail__media__img-link"
        }
    }

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

def isImageValid(img_url, img_resolution, min_resolution, max_resolution, img_contentType, valid_contentTypes):
    # Check if img parameters is valid
    if (not img_url) or (not img_contentType) or (not img_resolution):
        return False
    
    # Check if image content type is valid
    if not (img_contentType in valid_contentTypes):
        return False

    # Check if image resolution bigger than minResolution
    if (img_resolution[0] < min_resolution[0]) or (img_resolution[1] < min_resolution[1]):
        return False

    # Check if image resolution smaller than maxResolution
    if (img_resolution[0] > max_resolution[0]) or (img_resolution[1] > max_resolution[1]):
        return False        

    return True

def tryDownloadImage(imgUrl, search_engine, img_resolution, min_resolution, max_resolution, valid_contentTypes, save_dir):
    try:
        img_contentType = getImageContentType(imgUrl)

        if isImageValid(imgUrl, img_resolution, min_resolution, max_resolution, img_contentType, valid_contentTypes):
            image_fileName = getImageFileName(imgUrl, img_contentType)
            save_filePath = os.path.join(save_dir, image_fileName)

            if os.path.exists(save_filePath):
                return False

            downloadImage(imgUrl, save_filePath)
            print(imgUrl + " $$ " + image_fileName)
            return True 
    except Exception as ex:        
        print("tryDownloadImage: ", ex)

    return False

# Returns True if image was downloaded
def processImageGoogle(wd, search_engine, min_resolution, max_resolution, valid_contentTypes, saveDir):
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
            imgUrl = actual_image.get_attribute("src")

            if imgUrl.startswith("data:"):
                # print("Skip data: image")
                continue

            resolution = actual_resolution.get_attribute("innerHTML").split(SEARCH_ENGINES[search_engine]["image_resolution_divider"])
            resolution[0], resolution[1] = int(resolution[0]), int(resolution[1])

            if tryDownloadImage(imgUrl, search_engine, resolution, min_resolution, max_resolution, valid_contentTypes, saveDir):
                return True
    except Exception as ex:
        print("processImageGoogle: ", ex)   

    return False

# Returns True if image was downloaded
def processImageDuckDuckGo(wd, search_engine, min_resolution, max_resolution, valid_contentTypes, save_dir):             
    time.sleep(IMAGE_LOAD_SLEEP_TIME)

    # extract image urls    
    image_links = wd.find_elements_by_css_selector(SEARCH_ENGINES[search_engine]["image_link_selector"])  

    for image_link in image_links:                
        imgUrl = image_link.get_attribute("href")

        if imgUrl.startswith("data:"):
            continue

        #if tryDownloadImage(imgUrl, searchEngine, actual_resolution, minResolution, maxResolution, imageContentTypes, saveDir):
            #return True

    return False