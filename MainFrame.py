import wx
import io
import json
from pathlib import Path
from threading import Thread
from ImageScrapper import ImageScrapper
from pubsub import pub

from wx import * # when release, remove this line

# Main Window Consts
WINDOW_TITLE = "Завантаження зображень"
WINDOW_SIZE = (536, 430)
WINDOW_STYLE = wx.MINIMIZE_BOX | wx.SYSTEM_MENU | wx.CAPTION | wx.CLOSE_BOX | wx.CLIP_CHILDREN

# Element consts
ELEMENT_LEFT_MARGIN = 10
ELEMENT_TOP_MARGIN = 2

# Font consts
TEXT_FONT_SIZE = 12
TEXT_INPUT_FONT_SIZE = 12

# Other
SEARCH_ENGINES = ["Google", "DuckDuckGo", "Flickr", "PicSearch", "Pinterest"]

# Default values for each input
INPUT_DEFAULT_VALUES = {
    "search_query": "Wallpapers",
    "search_engine": SEARCH_ENGINES[0],
    "save_dir": "D:\\ScrappedImages\\",
    "max_images_count": 10,
    "min_resolution_width": 100, 
    "min_resolution_height": 100,
    "max_resolution_width": 1920, 
    "max_resolution_height": 1080,    
    "image_extension_jpg": True,
    "image_extension_png": True,
    "image_extension_gif": False
}

# Function for easy placing elements
def GetNextPos(prevElement, leftMargin = ELEMENT_LEFT_MARGIN, topMargin = ELEMENT_TOP_MARGIN):
    return (leftMargin, prevElement.GetPosition().y + prevElement.GetSize().y + topMargin)

class MainFrame(wx.Frame):    
    def __init__(self):
        # Fonts
        TEXT_FONT = wx.Font(TEXT_FONT_SIZE, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        TEXT_INPUT_FONT = wx.Font(TEXT_INPUT_FONT_SIZE, wx.DEFAULT, wx.NORMAL, wx.NORMAL)


        # Main Window Settings
        super().__init__(parent=None, title=WINDOW_TITLE, size=WINDOW_SIZE, style=WINDOW_STYLE)
        panel = wx.Panel(self)


        # Search Query
        self.search_query_label = wx.StaticText(panel, pos=(10, 10), label="Пошуковий запит")
        self.search_query_label.SetFont(TEXT_FONT)

        self.search_query = wx.TextCtrl(panel, pos=GetNextPos(self.search_query_label), size=(500, -1))
        self.search_query.SetFont(TEXT_INPUT_FONT)
        

        # Search Engine
        self.search_engine_label = wx.StaticText(panel, pos=GetNextPos(self.search_query, topMargin=10), label="Пошукова система")
        self.search_engine_label.SetFont(TEXT_FONT)

        self.search_engine = wx.ComboBox(panel, pos=GetNextPos(self.search_engine_label), size=(500, -1), choices=SEARCH_ENGINES)
        self.search_engine.SetFont(TEXT_INPUT_FONT)


        # Directory to save images
        self.save_dir_label = wx.StaticText(panel, pos=GetNextPos(self.search_engine, topMargin=10), label="Шлях до папки куди зберігати зображення")
        self.save_dir_label.SetFont(TEXT_FONT)

        self.save_dir = wx.DirPickerCtrl(panel, pos=GetNextPos(self.save_dir_label), size=(500, -1))
        self.save_dir.SetFont(TEXT_INPUT_FONT)


        # How much images save
        self.max_images_count_label = wx.StaticText(panel, pos=GetNextPos(self.save_dir, topMargin=10), label="Максимальна кількість збережених зображень")
        self.max_images_count_label.SetFont(TEXT_FONT)

        self.max_images_count = wx.SpinCtrl(panel, pos=GetNextPos(self.max_images_count_label), size=(500, -1), max=10000)
        self.max_images_count.SetFont(TEXT_INPUT_FONT)


        # Min resolution
        self.min_resolution_label = wx.StaticText(panel, pos=GetNextPos(self.max_images_count, topMargin=10), label="Мінімальна роздільна здатність")
        self.min_resolution_label.SetFont(TEXT_FONT)

        self.min_resolution_width = wx.SpinCtrl(panel, pos=GetNextPos(self.min_resolution_label), size=(100, -1), max=7680)
        
        self.min_resolution_wh_label = wx.StaticText(panel, pos=GetNextPos(self.min_resolution_label, leftMargin=120), label="x")
        self.min_resolution_wh_label.SetFont(TEXT_FONT)

        self.min_resolution_height = wx.SpinCtrl(panel, pos=GetNextPos(self.min_resolution_label, leftMargin=140), size=(100, -1), max=4320)


        # Max resolution
        self.max_resolution_label = wx.StaticText(panel, pos=GetNextPos(self.max_images_count, topMargin=10, leftMargin=260), label="Максимальна роздільна здатність")
        self.max_resolution_label.SetFont(TEXT_FONT)

        self.max_resolution_width = wx.SpinCtrl(panel, pos=GetNextPos(self.min_resolution_label, leftMargin=260), size=(100, -1), max=7680)
        
        self.max_resolution_wh_label = wx.StaticText(panel, pos=GetNextPos(self.min_resolution_label, leftMargin=370), label="x")
        self.max_resolution_wh_label.SetFont(TEXT_FONT)

        self.max_resolution_height = wx.SpinCtrl(panel, pos=GetNextPos(self.min_resolution_label, leftMargin=390), size=(100, -1), max=4320)


        # Image extension
        self.image_extension_label = wx.StaticText(panel, pos=GetNextPos(self.max_resolution_height, topMargin=10), label="Розширення зображення")
        self.image_extension_label.SetFont(TEXT_FONT)

        self.image_extension_jpg = wx.CheckBox(panel, label="JPG", pos=GetNextPos(self.image_extension_label), size=(60, -1))
        self.image_extension_jpg.SetFont(TEXT_FONT)

        self.image_extension_png = wx.CheckBox(panel, label="PNG", pos=GetNextPos(self.image_extension_label, leftMargin=80), size=(60, -1))
        self.image_extension_png.SetFont(TEXT_FONT)

        self.image_extension_gif = wx.CheckBox(panel, label="GIF", pos=GetNextPos(self.image_extension_label, leftMargin=150), size=(60, -1))
        self.image_extension_gif.SetFont(TEXT_FONT)


        # Download
        self.download = wx.Button(panel, label="Завантажити", pos=GetNextPos(self.image_extension_gif, topMargin=10), size=(200, 30))

        # Gauge progress
        self.gauge = wx.Gauge(panel, range=100, pos=GetNextPos(self.image_extension_gif, topMargin=10, leftMargin=230), size=(280, 30))        

        # Menu
        self.initMenu()

        # Load default values
        self.setInputValues(INPUT_DEFAULT_VALUES)

        # Events
        self.Bind(wx.EVT_TEXT, self.onTextCtrlKeyPress)
        self.download.Bind(wx.EVT_BUTTON, self.onDownloadClick)
        self.Bind(wx.EVT_CLOSE, self.onClose)

        # Subscribes
        pub.subscribe(self.onDownloadProgressChanged, 'downloadProgressChanged')
        pub.subscribe(self.onDownloadFinished, 'downloadFinished')        

        # Properties
        self.current_settings_path = None
        self.updateProjectNameInTitle()

        self._image_scrapper = None        

        # Show form
        self.Center()
        self.Show()

    def getInputValues(self):
        return {
            "search_query": self.search_query.GetValue(),
            "search_engine": self.search_engine.GetValue(),
            "save_dir": self.save_dir.GetPath(),
            "max_images_count": self.max_images_count.GetValue(),
            "min_resolution_width": self.min_resolution_width.GetValue(), 
            "min_resolution_height": self.min_resolution_height.GetValue(),
            "max_resolution_width": self.max_resolution_width.GetValue(), 
            "max_resolution_height": self.max_resolution_height.GetValue(),    
            "image_extension_jpg": self.image_extension_jpg.GetValue(),
            "image_extension_png": self.image_extension_png.GetValue(),
            "image_extension_gif": self.image_extension_gif.GetValue()
        }

    def setInputValues(self, input_values):     
        self.search_query.SetValue(input_values["search_query"])
        self.search_engine.SetValue(input_values["search_engine"])
        self.save_dir.SetPath(input_values["save_dir"])
        self.max_images_count.SetValue(input_values["max_images_count"])
        self.min_resolution_width.SetValue(input_values["min_resolution_width"])
        self.min_resolution_height.SetValue(input_values["min_resolution_height"])
        self.max_resolution_width.SetValue(input_values["max_resolution_width"])
        self.max_resolution_height.SetValue(input_values["max_resolution_height"])
        self.image_extension_jpg.SetValue(input_values["image_extension_jpg"])
        self.image_extension_png.SetValue(input_values["image_extension_png"])
        self.image_extension_gif.SetValue(input_values["image_extension_gif"])

    def initMenu(self):    
        menu_bar = wx.MenuBar() 

        file_menu = wx.Menu() 

        create_project = wx.MenuItem(file_menu, id=wx.ID_ANY, text = "Створити проект\tCtrl+N", kind = wx.ITEM_NORMAL) 
        file_menu.Append(create_project) 		

        open_project = wx.MenuItem(file_menu, id=wx.ID_ANY, text = "Відкрити проект\tCtrl+O", kind = wx.ITEM_NORMAL) 
        file_menu.Append(open_project)         		

        file_menu.AppendSeparator()

        save_project = wx.MenuItem(file_menu, id=wx.ID_ANY, text = "Зберегти\tCtrl+S", kind = wx.ITEM_NORMAL) 
        file_menu.Append(save_project) 	       

        save_project_as = wx.MenuItem(file_menu, id=wx.ID_ANY, text = "Зберегти як\tCtrl+Shift+S", kind = wx.ITEM_NORMAL) 
        file_menu.Append(save_project_as) 	          

        file_menu.AppendSeparator()

        exit_app = wx.MenuItem(file_menu, id=wx.ID_ANY, text = "Вихід\tCtrl+Q", kind = wx.ITEM_NORMAL) 
        file_menu.Append(exit_app) 		

        menu_bar.Append(file_menu, 'Файл') 	
        self.SetMenuBar(menu_bar)        

        # Bind handlers
        self.Bind(wx.EVT_MENU, self.createProjectHandler, create_project)
        self.Bind(wx.EVT_MENU, self.openProjectHandler, open_project)    
        self.Bind(wx.EVT_MENU, self.saveProjectHandler, save_project)  
        self.Bind(wx.EVT_MENU, self.saveProjectAsHandler, save_project_as)  
        self.Bind(wx.EVT_MENU, self.exitAppHandler, exit_app)    

    def readDictFromJson(self, json_path):
        try:
            with io.open(json_path, 'r', encoding='utf-8') as json_file:
                return json.load(json_file)
        except:
            return None

    def saveDictToJson(self, json_path, data):
        try:
            with io.open(json_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False))
            return True
        except:
            return None

    def updateProjectNameInTitle(self, is_saved=False):
        new_title = WINDOW_TITLE + " − "

        if self.current_settings_path:
            new_title += Path(self.current_settings_path).stem
        else:
            new_title += "Новий проект"

        if not is_saved:
            new_title += "*"

        self.SetTitle(new_title)

    def createProjectHandler(self, event):
        if self.current_settings_path:
            dlg = wx.MessageBox("Ви впевнені, що хочете створити новий проект?", "Підтвердження", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION )
            if dlg == wx.YES:
                self.current_settings_path = None
                self.setInputValues(INPUT_DEFAULT_VALUES)
                self.updateProjectNameInTitle()

    def openProjectHandler(self, event):
        dlg = wx.FileDialog(self, message="Open", defaultFile="project.iss", wildcard="ImageScrapper Settings (*.iss)|*.iss", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.current_settings_path = dlg.GetPath()            
            input_values = self.readDictFromJson(self.current_settings_path)
            if input_values:
                self.setInputValues(input_values)
                self.updateProjectNameInTitle(True)
            else:
                wx.MessageBox("Виникла помилка при спробі завантажити даний файл!")                
        dlg.Destroy() 

    def saveProjectHandler(self, event):
        if self.current_settings_path:
            if self.saveDictToJson(self.current_settings_path, self.getInputValues()):
                self.updateProjectNameInTitle(True)
            else:
                wx.MessageBox("Виникла помилка при спробі зберегти файл!") 
        else:
            self.saveProjectAsHandler(event)

    def saveProjectAsHandler(self, event):
        dlg = wx.FileDialog(self, message="Save as", defaultFile="project.iss",  wildcard="ImageScrapper Settings (*.iss)|*.iss", style=wx.FD_SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            self.current_settings_path = dlg.GetPath()
            if self.saveDictToJson(self.current_settings_path, self.getInputValues()):
                self.updateProjectNameInTitle(True)
                wx.MessageBox("Файл успішно збережено!") 
            else:
                wx.MessageBox("Виникла помилка при спробі зберегти файл!") 
        dlg.Destroy() 

    def onTextCtrlKeyPress(self, event):
        input_values = self.readDictFromJson(self.current_settings_path)
        if input_values:
            self.updateProjectNameInTitle(self.getInputValues() == input_values)            

    def exitAppHandler(self, event):
        self.Close()              

    def onDownloadClick(self, event):
        if self.search_engine.GetValue() not in SEARCH_ENGINES:
            wx.MessageBox("Виберіть пошукову систему зі списку!")
            return

        image_contentTypes = []
        
        if self.image_extension_jpg.IsChecked():
            image_contentTypes.append("image/jpg")
            image_contentTypes.append("image/jpeg")

        if self.image_extension_png.IsChecked():
            image_contentTypes.append("image/png")

        if self.image_extension_gif.IsChecked():
            image_contentTypes.append("image/gif")

        if len(image_contentTypes) == 0:
            wx.MessageBox("Виберіть хоча б одне розширення зображення!")
            return        

        minResolution = (self.min_resolution_width.Value, self.min_resolution_height.Value)
        maxResolution = (self.max_resolution_width.Value, self.max_resolution_height.Value)        

        self._image_scrapper = ImageScrapper()
        Thread(target=self._image_scrapper.downloadImages,
            args=(self.search_query.Value, 
            self.search_engine.Value, 
            self.max_images_count.Value, 
            minResolution, 
            maxResolution,
            image_contentTypes,
            self.save_dir.Path)).start()

        self.gauge.SetValue(0)
        self.download.Enabled = False

    def onDownloadProgressChanged(self, progress):
        self.gauge.SetValue(progress)

    def onDownloadFinished(self):
        wx.MessageBox("Завантаження завершено!")
        self.download.Enabled = True

    def onClose(self, event):
        if self._image_scrapper:
            self._image_scrapper.terminate()
        event.Skip()

if __name__ == '__main__':
    app = wx.App()
    frame = MainFrame()
    app.MainLoop()