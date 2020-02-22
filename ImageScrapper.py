import time
from pathlib import Path
from selenium import webdriver
import urllib3

from SearchEngines import SEARCH_ENGINES
from SearchEngines import processImageGoogle
from SearchEngines import processImageDuckDuckGo

from pubsub import pub

SLEEP_TIME_AFTER_SCROLL = 2

SE_PROCESS_IMAGE = {
    "Google": processImageGoogle,
    "DuckDuckGo": processImageDuckDuckGo
}

class ImageScrapper:
    def __init__(self):        
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        # variable to allow terminate this thread
        self._running = True

    def terminate(self):
        self._running = False

    def _tryLoadMoreImages(self, wd, search_engine):
        try:
            if SEARCH_ENGINES[search_engine]["selectors"]["load_more"]:
                load_more_button = wd.find_element_by_css_selector(SEARCH_ENGINES[search_engine]["selectors"]["load_more"])
                if load_more_button:
                    wd.execute_script("document.querySelector('"+SEARCH_ENGINES[search_engine]["selectors"]["load_more"]+"').click();")
        except Exception as ex:
            print("_tryLoadMoreImages: ", ex)
            pass

    def _findImagesAndDownload(self, search_query, search_engine, max_images_count, min_resolution, max_resolution, valid_contentTypes, save_dir):
        def scroll_to_end(wd):
            wd.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SLEEP_TIME_AFTER_SCROLL)    

        # build the google query
        search_url = SEARCH_ENGINES[search_engine]["search_url"]

        # create chrome driver
        options = webdriver.ChromeOptions()
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        wd = webdriver.Chrome(chrome_options=options)

        # load the page
        wd.get(search_url.format(q=search_query))

        results_start = 0
        downloaded_images_count = 0

        while self._running and downloaded_images_count < max_images_count:
            scroll_to_end(wd)

            # get all image thumbnail results
            thumbnail_results = wd.find_elements_by_css_selector(SEARCH_ENGINES[search_engine]["selectors"]["thumbnail"])
            images_resolution = wd.find_elements_by_css_selector(SEARCH_ENGINES[search_engine]["selectors"]["image_resolution"])

            thumbnail_count = len(thumbnail_results)
            resolution_count = len(images_resolution)

            if thumbnail_count != resolution_count:
                print("Thumbnail and resolution count mismatch!")
                continue
            
            print(f"Found: {thumbnail_count} search results. Extracting links from {results_start}:{thumbnail_count}")
            
            for image, resolution_el in zip(thumbnail_results[results_start:thumbnail_count], images_resolution[results_start:thumbnail_count]): 
                # if thread was terminated
                if not self._running:
                    break

                try:
                    image.click()
                except:
                    continue

                resolution = resolution_el.get_attribute("innerHTML").split(SEARCH_ENGINES[search_engine]["image_resolution_divider"])
                resolution[0], resolution[1] = int(resolution[0]), int(resolution[1])

                # Check if image resolution bigger than minResolution
                if (resolution[0] < min_resolution[0]) or (resolution[1] < min_resolution[1]):
                    continue

                # Check if image resolution smaller than maxResolution
                if (resolution[0] > max_resolution[0]) or (resolution[1] > max_resolution[1]):
                    continue

                # call processImage function depending on search engine
                if SE_PROCESS_IMAGE[search_engine](wd, search_engine, min_resolution, max_resolution, valid_contentTypes, save_dir):
                    downloaded_images_count += 1                    
                    pub.sendMessage('downloadProgressChanged', progress=(downloaded_images_count * 100) // max_images_count)
                    if downloaded_images_count >= max_images_count:
                        break
            else:            
                print("Found:", downloaded_images_count, "image links, looking for more ...")
                self._tryLoadMoreImages(wd, search_engine)

            # move the result startpoint further down
            results_start = len(thumbnail_results)    
        wd.close()        

    def downloadImages(self, search_query, search_engine, max_images_count, min_resolution, max_resolution, valid_contentTypes, save_dir):        
        try:
            # create directory where images will be saved
            Path(save_dir).mkdir(parents=True, exist_ok=True)

            self._findImagesAndDownload(search_query, search_engine, max_images_count, min_resolution, max_resolution, valid_contentTypes, save_dir)

            if self._running:
                pub.sendMessage('downloadFinished')
        except Exception as ex:
            print("downloadImages: ", ex)