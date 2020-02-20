import time
from pathlib import Path
from selenium import webdriver

from SearchEngines import SEARCH_ENGINES
from SearchEngines import processImageGoogle

SLEEP_TIME_AFTER_SCROLL = 2
SE_PROCESS_IMAGE = {
    "Google": processImageGoogle
}

class ImageScrapper:
    def __init__(self):
        # variable to allow terminate this thread
        self._running = True

    def terminate(self):
        self._running = False

    def _tryLoadMoreImages(self, wd, searchEngine):
        try:
            load_more_button = wd.find_element_by_css_selector(SEARCH_ENGINES[searchEngine]["load_more_css_selector"])
            if load_more_button:
                wd.execute_script("document.querySelector('"+SEARCH_ENGINES[searchEngine]["load_more_css_selector"]+"').click();")
        except Exception as ex:
            print(ex)
            pass

    def _findImagesAndDownload(self, searchQuery, searchEngine, maxImagesCount, minResolution, maxResolution, imageContentTypes, saveDir, results_start=0):
        def scroll_to_end(wd):
            wd.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SLEEP_TIME_AFTER_SCROLL)    

        # build the google query
        search_url = SEARCH_ENGINES[searchEngine]["search_url"]

        wd = webdriver.Chrome()

        # load the page
        wd.get(search_url.format(q=searchQuery))
        
        image_count = 0

        while self._running and image_count < maxImagesCount:
            scroll_to_end(wd)

            # get all image thumbnail results
            thumbnail_results = wd.find_elements_by_css_selector(SEARCH_ENGINES[searchEngine]["thumbnail_css_selector"])
            number_results = len(thumbnail_results)
            
            print(f"Found: {number_results} search results. Extracting links from {results_start}:{number_results}")
            
            for img in thumbnail_results[results_start:number_results]: 
                # if thread was terminated
                if not self._running:
                    break

                # call processImage function depending on search engine
                if SE_PROCESS_IMAGE[searchEngine](wd, img, searchEngine, minResolution, maxResolution, imageContentTypes, saveDir):
                    image_count += 1
                    if image_count >= maxImagesCount:
                        break
            else:            
                print("Found:", image_count, "image links, looking for more ...")
                self._tryLoadMoreImages(wd, searchEngine)

            # move the result startpoint further down
            results_start = len(thumbnail_results)    
        wd.close()

    def downloadImages(self, searchQuery, searchEngine, maxImagesCount, minResolution, maxResolution, imageContentTypes, saveDir):        
        try:
            # create directory where images will be saved
            Path(saveDir).mkdir(parents=True, exist_ok=True)

            self._findImagesAndDownload(searchQuery, searchEngine, maxImagesCount, minResolution, maxResolution, imageContentTypes, saveDir)
        except Exception as ex:
            print(ex)