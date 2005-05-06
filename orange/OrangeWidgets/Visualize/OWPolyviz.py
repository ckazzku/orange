"""
<name>Polyviz</name>
<description>Shows data using Polyviz visualization method</description>
<icon>icons/Polyviz.png</icon>
<priority>3150</priority>
"""
# Polyviz.py
#
# Show data using Polyviz visualization method
# 

from OWWidget import *
from random import betavariate 
from OWPolyvizGraph import *
import OWVisAttrSelection
from OWkNNOptimization import *
from time import time
from math import pow
import OWToolbars

###########################################################################################
##### WIDGET : Polyviz visualization
###########################################################################################
class OWPolyviz(OWWidget):
    settingsList = ["graph.pointWidth", "lineLength", "graph.jitterSize", "graphCanvasColor", "graph.globalValueScaling", "graph.scaleFactor",
                    "graph.enabledLegend", "graph.showFilledSymbols", "graph.optimizedDrawing", "graph.useDifferentSymbols", "autoSendSelection",
                    "graph.useDifferentColors", "graph.tooltipKind", "graph.tooltipValue", "toolbarSelection", "VizRankClassifierName"]
    jitterSizeNums = [0.0, 0.1,   0.5,  1,  2 , 3,  4 , 5, 7, 10, 15, 20]
    jitterSizeList = [str(x) for x in jitterSizeNums]
    scaleFactorNums = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.2, 2.4, 2.6, 2.8, 3.0]
    scaleFactorList = [str(x) for x in scaleFactorNums]
        
    def __init__(self,parent=None, signalManager = None):
        OWWidget.__init__(self, parent, signalManager, "Polyviz", TRUE)

        #add a graph widget
        self.box = QVBoxLayout(self.mainArea)
        self.graph = OWPolyvizGraph(self, self.mainArea)
        self.box.addWidget(self.graph)

        self.inputs = [("Classified Examples", ExampleTableWithClass, self.cdata), ("Attribute Selection List", AttributeList, self.attributeSelection)]
        self.outputs = [("Selected Examples", ExampleTableWithClass), ("Unselected Examples", ExampleTableWithClass), ("Example Distribution", ExampleTableWithClass),("Attribute Selection List", AttributeList)]

        #set default settings
        self.graph.pointWidth = 5
        self.lineLength = 2
        self.graph.scaleFactor = 1.0
        self.graph.globalValueScaling = 0
        self.graph.jitterSize = 1
        self.attributeReverse = {}  # dictionary with bool values - do we want to reverse attribute values
        self.graph.enabledLegend = 1
        self.graph.showFilledSymbols = 1
        self.graph.optimizedDrawing = 1
        self.graph.useDifferentSymbols = 0
        self.graph.useDifferentColors = 1
        self.autoSendSelection = 1
        self.rotateAttributes = 0
        self.graph.tooltipKind = 0
        self.graph.tooltipValue = 0
        self.toolbarSelection = 0
        self.graphCanvasColor = str(Qt.white.name())
        self.VizRankClassifierName = "VizRank classifier (Polyviz)"
        
        self.data = None
        self.attributeSelectionList = None

        #load settings
        self.loadSettings()

        # add a settings dialog and initialize its values
        self.tabs = QTabWidget(self.space, 'tabWidget')
        self.GeneralTab = QVGroupBox(self)
        self.SettingsTab = QVGroupBox(self, "Settings")
        self.tabs.insertTab(self.GeneralTab, "General")
        self.tabs.insertTab(self.SettingsTab, "Settings")

        #GUI
        self.statusBar = QStatusBar(self.mainArea)
        self.box.addWidget(self.statusBar)
        self.graph.updateSettings(statusBar = self.statusBar)
        self.statusBar.message("")

        #add controls to self.controlArea widget
        self.shownAttribsGroup = OWGUI.widgetBox(self.GeneralTab, " Shown attributes ")
        self.hbox2 = OWGUI.widgetBox(self.GeneralTab, "", orientation = "horizontal")
        self.hiddenAttribsGroup = OWGUI.widgetBox(self.GeneralTab, " Hidden attributes ")
        self.attrOrderingButtons = QVButtonGroup("Attribute ordering", self.GeneralTab)

        self.shownAttribsLB = QListBox(self.shownAttribsGroup)
        self.shownAttribsLB.setSelectionMode(QListBox.Extended)

        self.hiddenAttribsLB = QListBox(self.hiddenAttribsGroup)
        self.hiddenAttribsLB.setSelectionMode(QListBox.Extended)
        
        self.optimizationDlgButton = QPushButton('VizRank optimization dialog', self.attrOrderingButtons)
        OWGUI.checkBox(self.attrOrderingButtons, self, "rotateAttributes", "Rotate attributes", tooltip = "When searching for optimal projections also evaluate projections with rotated attributes. \nThis will significantly increase the number of possible projections.")

        self.optimizationDlg = kNNOptimization(None, self.signalManager, self.graph, "Polyviz")
        self.graph.kNNOptimization = self.optimizationDlg
        self.optimizationDlg.optimizeGivenProjectionButton.show()

        self.zoomSelectToolbar = OWToolbars.ZoomSelectToolbar(self, self.GeneralTab, self.graph, self.autoSendSelection)
        self.graph.autoSendSelectionCallback = self.selectionChanged
        self.connect(self.zoomSelectToolbar.buttonSendSelections, SIGNAL("clicked()"), self.sendSelections)

        self.hbox = OWGUI.widgetBox(self.shownAttribsGroup, "", orientation = "horizontal")
        self.buttonUPAttr = QPushButton("Attr UP", self.hbox)
        self.buttonDOWNAttr = QPushButton("Attr DOWN", self.hbox)

        self.attrAddButton = QPushButton("Add attr.", self.hbox2)
        self.attrRemoveButton = QPushButton("Remove attr.", self.hbox2)

        # ####################################
        # SETTINGS TAB
        # #####
        OWGUI.hSlider(self.SettingsTab, self, 'graph.pointWidth', box='Point width', minValue=1, maxValue=15, step=1, callback = self.updateGraph, ticks=1)
        OWGUI.hSlider(self.SettingsTab, self, 'lineLength', box='Line length', minValue=1, maxValue=5, step=1, callback = self.updateValues, ticks=1)

        box = OWGUI.widgetBox(self.SettingsTab, " Jittering options ")
        OWGUI.comboBoxWithCaption(box, self, "graph.jitterSize", 'Jittering size (% of size)  ', callback = self.setJitteringSize, items = self.jitterSizeNums, sendSelectedValue = 1, valueType = float)

        OWGUI.comboBoxWithCaption(self.SettingsTab, self, "graph.scaleFactor", 'Scale point position by: ', box = " Point scaling ", callback = self.updateGraph, items = self.scaleFactorNums, sendSelectedValue = 1, valueType = float)

        box2 = OWGUI.widgetBox(self.SettingsTab, " General graph settings ")
        OWGUI.checkBox(box2, self, 'graph.enabledLegend', 'Show legend', callback = self.updateGraph)
        OWGUI.checkBox(box2, self, 'graph.globalValueScaling', 'Use global value scaling', callback = self.setGlobalValueScaling, tooltip = "Scale values of all attributes based on min and max value of all attributes. Usually unchecked.")
        OWGUI.checkBox(box2, self, 'graph.optimizedDrawing', 'Optimize drawing', callback = self.updateGraph, tooltip = "Speed up drawing by drawing all point belonging to one class value at once")
        OWGUI.checkBox(box2, self, 'graph.useDifferentSymbols', 'Use different symbols', callback = self.updateGraph, tooltip = "Show different class values using different symbols")
        OWGUI.checkBox(box2, self, 'graph.useDifferentColors', 'Use different colors', callback = self.updateGraph, tooltip = "Show different class values using different colors")
        OWGUI.checkBox(box2, self, 'graph.showFilledSymbols', 'Show filled symbols', callback = self.updateGraph)

        box3 = OWGUI.widgetBox(self.SettingsTab, " Tooltips settings ")
        OWGUI.comboBox(box3, self, "graph.tooltipKind", items = ["Show line tooltips", "Show visible attributes", "Show all attributes"], callback = self.updateGraph)
        OWGUI.comboBox(box3, self, "graph.tooltipValue", items = ["Tooltips show data values", "Tooltips show spring values"], callback = self.updateGraph, tooltip = "Do you wish that tooltips would show you original values of visualized attributes or the 'spring' values (values between 0 and 1). \nSpring values are scaled values that are used for determining the position of shown points. Observing these values will therefore enable you to \nunderstand why the points are placed where they are.")


        box4 = OWGUI.widgetBox(self.SettingsTab, " Sending selection ")
        OWGUI.checkBox(box4, self, 'autoSendSelection', 'Auto send selected data', callback = self.selectionChanged, tooltip = "Send signals with selected data whenever the selection changes.")

        # ####
        self.gSetCanvasColorB = QPushButton("Canvas Color", self.SettingsTab)
        self.connect(self.gSetCanvasColorB, SIGNAL("clicked()"), self.setGraphCanvasColor)


        # ####################################
        #K-NN OPTIMIZATION functionality
        self.optimizationDlg.useHeuristicToFindAttributeOrderCheck.show()
        self.connect(self.optimizationDlg.optimizeGivenProjectionButton, SIGNAL("clicked()"), self.optimizeGivenProjectionClick)
        self.connect(self.optimizationDlgButton, SIGNAL("clicked()"), self.optimizationDlg.reshow)
        self.connect(self.optimizationDlg.resultList, SIGNAL("selectionChanged()"),self.showSelectedAttributes)
        self.connect(self.optimizationDlg.startOptimizationButton , SIGNAL("clicked()"), self.optimizeSeparation)
        self.connect(self.optimizationDlg.evaluateProjectionButton, SIGNAL("clicked()"), self.evaluateCurrentProjection)
        #self.connect(self.optimizationDlg.saveProjectionButton, SIGNAL("clicked()"), self.saveCurrentProjection)
        self.connect(self.optimizationDlg.showKNNCorrectButton, SIGNAL("clicked()"), self.showKNNCorect)
        self.connect(self.optimizationDlg.showKNNWrongButton, SIGNAL("clicked()"), self.showKNNWrong)
        self.connect(self.shownAttribsLB, SIGNAL('doubleClicked(QListBoxItem *)'), self.reverseSelectedAttribute)

        self.connect(self.buttonUPAttr, SIGNAL("clicked()"), self.moveAttrUP)
        self.connect(self.buttonDOWNAttr, SIGNAL("clicked()"), self.moveAttrDOWN)

        self.connect(self.attrAddButton, SIGNAL("clicked()"), self.addAttribute)
        self.connect(self.attrRemoveButton, SIGNAL("clicked()"), self.removeAttribute)

        self.connect(self.graphButton, SIGNAL("clicked()"), self.graph.saveToFile)
        
        # add a settings dialog and initialize its values
        self.activateLoadedSettings()

        self.resize(900, 700)


    # #########################
    # OPTIONS
    # #########################
    def activateLoadedSettings(self):
        self.graph.setCanvasBackground(QColor(self.graphCanvasColor))
        apply([self.zoomSelectToolbar.actionZooming, self.zoomSelectToolbar.actionRectangleSelection, self.zoomSelectToolbar.actionPolygonSelection][self.toolbarSelection], [])
        self.optimizationDlg.changeLearnerName(self.VizRankClassifierName)

    # #########################
    # KNN OPTIMIZATION BUTTON EVENTS
    # #########################

    def saveCurrentProjection(self):
        qname = QFileDialog.getSaveFileName( os.path.realpath(".") + "/Polyviz_projection.tab", "Orange Example Table (*.tab)", self, "", "Save File")
        if qname.isEmpty(): return
        name = str(qname)
        if len(name) < 4 or name[-4] != ".":
            name = name + ".tab"

        self.graph.saveProjectionAsTabData(name, self.getShownAttributeList(), self.attributeReverse)

    # evaluate knn accuracy on current projection
    def evaluateCurrentProjection(self):
        acc, results = self.graph.getProjectionQuality(self.getShownAttributeList(), self.attributeReverse)
        if self.data.domain.classVar.varType == orange.VarTypes.Continuous:
            QMessageBox.information( None, "Polyviz", 'Mean square error of kNN model is %.2f'%(acc), QMessageBox.Ok + QMessageBox.Default)
        else:
            if self.optimizationDlg.getQualityMeasure() == CLASS_ACCURACY:
                QMessageBox.information( None, "Polyviz", 'Classification accuracy of kNN model is %.2f %%'%(acc), QMessageBox.Ok + QMessageBox.Default)
            elif self.optimizationDlg.getQualityMeasure() == AVERAGE_CORRECT:
                QMessageBox.information( None, "Polyviz", 'Average probability of correct classification is %.2f %%'%(acc), QMessageBox.Ok + QMessageBox.Default)
            else:
                QMessageBox.information( None, "Polyviz", 'Brier score of kNN model is %.2f' % (acc), QMessageBox.Ok + QMessageBox.Default)
            
    # show quality of knn model by coloring accurate predictions with darker color and bad predictions with light color        
    def showKNNCorect(self):
        self.graph.updateData(self.getShownAttributeList(), self.attributeReverse, showKNNModel = 1, showCorrect = 1)
        self.graph.update()
        self.repaint()

    # show quality of knn model by coloring accurate predictions with lighter color and bad predictions with dark color
    def showKNNWrong(self):
        self.graph.updateData(self.getShownAttributeList(), self.attributeReverse, showKNNModel = 1, showCorrect = 0)
        self.graph.update()
        self.repaint()
        
    def optimizeSeparation(self):
        if self.data == None: return
        
        text = str(self.optimizationDlg.attributeCountCombo.currentText())
        if text == "ALL": maxLen = len(listOfAttributes)
        else:             maxLen = int(text)

        if self.rotateAttributes: reverseList = None
        else: reverseList = self.attributeReverse
        
        if self.optimizationDlg.getOptimizationType() == self.optimizationDlg.EXACT_NUMBER_OF_ATTRS: minLen = maxLen
        else: minLen = 3

        self.optimizationDlg.clearResults()
        self.optimizationDlg.disableControls()

        # ################################################################################################
        # use the heuristic to test only most interesting attribute orders
        if self.optimizationDlg.useHeuristicToFindAttributeOrders:
            self.optimizationDlg.setStatusBarText("Evaluating attributes...")
            attrs, attrsByClass = OWVisAttrSelection.findAttributeGroupsForRadviz(self.data, OWVisAttrSelection.S2NMeasureMix())
            self.optimizationDlg.setStatusBarText("")

            self.graph.getOptimalSeparationUsingHeuristicSearch(attrs, attrsByClass, minLen, maxLen, reverseList, self.optimizationDlg.addResult)

        # ################################################################################################
        # evaluate all attribute orders
        else:
            listOfAttributes = self.optimizationDlg.getEvaluatedAttributes(self.data)
            possibilities = 0
            for i in range(minLen, maxLen+1):
                possibilities += combinations(i, len(listOfAttributes))*fact(i-1)/2

                if not self.rotateAttributes: possibilities += combinations(i, len(listOfAttributes)) * fact(i-1)
                else: possibilities += combinations(i, len(listOfAttributes)) * fact(i-1) * pow(2, i)/2

            self.graph.totalPossibilities = int(possibilities)
            self.graph.triedPossibilities = 0

            if self.graph.totalPossibilities > 200000:
                self.warning("There are %s possible polyviz projections with this set of attributes"% (createStringFromNumber(self.graph.totalPossibilities)))

            try:
                self.graph.getOptimalSeparation(listOfAttributes, minLen, maxLen, reverseList, self.optimizationDlg.addResult)
            except:
                type, val, traceback = sys.exc_info()
                sys.excepthook(type, val, traceback)  # print the exception

        self.optimizationDlg.enableControls()
        self.optimizationDlg.finishedAddingResults()

    # ################################################################################################
    # try to find a better projection than the currently shown projection by adding other attributes to the projection and evaluating projections
    def optimizeGivenProjectionClick(self, numOfBestAttrs = -1, maxProjLen = -1):
        if numOfBestAttrs == -1:
            if self.data and len(self.data.domain.attributes) > 1000:
                (text, ok) = QInputDialog.getText('Qt Optimize Current Projection', 'How many of the best ranked attributes do you wish to test?')
                if not ok: return
                numOfBestAttrs = int(str(text))
            else: numOfBestAttrs = 10000
        
        self.optimizationDlg.disableControls()
        acc = self.graph.getProjectionQuality(self.getShownAttributeList(), self.attributeReverse)[0]
        # try to find a better separation than the one that is currently shown
        if self.rotateAttributes:
            attrs = self.getShownAttributeList()
            reverse = [self.attributeReverse[attr] for attr in attrs]
            self.graph.optimizeGivenProjection(attrs, reverse, acc, self.optimizationDlg.getEvaluatedAttributes(self.data)[:numOfBestAttrs], self.optimizationDlg.addResult)
        else:
            self.graph.optimizeGivenProjection(self.getShownAttributeList(), None, acc, self.optimizationDlg.getEvaluatedAttributes(self.data)[:numOfBestAttrs], self.optimizationDlg.addResult, restartWhenImproved = 1, maxProjectionLen = maxProjLen)
        self.optimizationDlg.enableControls()
        self.optimizationDlg.finishedAddingResults()

    def reverseSelectedAttribute(self, item):
        text = str(item.text())
        name = text[:-2]
        self.attributeReverse[name] = not self.attributeReverse[name]

        for i in range(self.shownAttribsLB.count()):
            if str(self.shownAttribsLB.item(i).text()) == str(item.text()):
                self.shownAttribsLB.removeItem(i)
                if self.attributeReverse[name] == 1:    self.shownAttribsLB.insertItem(name + ' -', i)
                else:                                   self.shownAttribsLB.insertItem(name + ' +', i)
                self.shownAttribsLB.setCurrentItem(i)
                self.updateGraph()
                return
        
  
    # ####################################
    # show selected interesting projection
    def showSelectedAttributes(self):
        val = self.optimizationDlg.getSelectedProjection()
        if not val: return
        (accuracy, other_results, tableLen, attrList, tryIndex, attrReverseList) = val
        
        # check if all attributes in list really exist in domain
        for attr in attrList:
            if not self.graph.attributeNameIndex.has_key(attr):
                return
        
        self.shownAttribsLB.clear()
        self.hiddenAttribsLB.clear()

        reverseDict = dict([(attrList[i], attrReverseList[i]) for i in range(len(attrList))])

        for attr in attrList:
            if reverseDict[attr]: self.shownAttribsLB.insertItem(attr + " -")
            else: self.shownAttribsLB.insertItem(attr + " +")
            self.attributeReverse[attr] = reverseDict[attr]

        for attr in self.data.domain:
            if attr.name not in attrList:
                self.hiddenAttribsLB.insertItem(attr.name + " +")
                self.attributeReverse[attr.name] = 0

        self.updateGraph()

    # send signals with selected and unselected examples as two datasets
    def sendSelections(self):   
        if not self.data: return
        (selected, unselected, merged) = self.graph.getSelectionsAsExampleTables(self.getShownAttributeList(), self.attributeReverse)
        self.send("Selected Examples",selected)
        self.send("Unselected Examples",unselected)
        self.send("Example Distribution", merged)

    def sendShownAttributes(self):
        self.send("Attribute Selection List", self.getShownAttributeList())
        
    # ####################
    # LIST BOX FUNCTIONS
    # ####################

    # move selected attribute in "Attribute Order" list one place up
    def moveAttrUP(self):
        for i in range(self.shownAttribsLB.count()):
            if self.shownAttribsLB.isSelected(i) and i != 0:
                text = self.shownAttribsLB.text(i)
                self.shownAttribsLB.removeItem(i)
                self.shownAttribsLB.insertItem(text, i-1)
                self.shownAttribsLB.setSelected(i-1, TRUE)
        self.updateGraph()

    # move selected attribute in "Attribute Order" list one place down  
    def moveAttrDOWN(self):
        count = self.shownAttribsLB.count()
        for i in range(count-2,-1,-1):
            if self.shownAttribsLB.isSelected(i):
                text = self.shownAttribsLB.text(i)
                self.shownAttribsLB.removeItem(i)
                self.shownAttribsLB.insertItem(text, i+1)
                self.shownAttribsLB.setSelected(i+1, TRUE)
        self.updateGraph()

    def addAttribute(self):
        count = self.hiddenAttribsLB.count()
        pos   = self.shownAttribsLB.count()
        for i in range(count-1, -1, -1):
            if self.hiddenAttribsLB.isSelected(i):
                text = self.hiddenAttribsLB.text(i)
                self.hiddenAttribsLB.removeItem(i)
                self.shownAttribsLB.insertItem(text, pos)

        if self.graph.globalValueScaling == 1:
            self.graph.rescaleAttributesGlobaly(self.data, self.getShownAttributeList())
        self.updateGraph()
        #self.graph.replot()

    def removeAttribute(self):
        count = self.shownAttribsLB.count()
        pos   = self.hiddenAttribsLB.count()
        for i in range(count-1, -1, -1):
            if self.shownAttribsLB.isSelected(i):
                text = self.shownAttribsLB.text(i)
                self.shownAttribsLB.removeItem(i)
                self.hiddenAttribsLB.insertItem(text, pos)
        if self.graph.globalValueScaling == 1:
            self.graph.rescaleAttributesGlobaly(self.data, self.getShownAttributeList())
        self.updateGraph()
        #self.graph.replot()

    # #####################

    def updateGraph(self, *args):
        self.graph.updateData(self.getShownAttributeList(), self.attributeReverse)
        self.graph.update()
        self.repaint()
    
    def getShownAttributeList(self):
        return [str(self.shownAttribsLB.text(i))[:-2] for i in range(self.shownAttribsLB.count())]

    def setShownAttributeList(self, data, shownAttributes = None):
        self.shownAttribsLB.clear()
        self.hiddenAttribsLB.clear()

        if data == None: return

        if shownAttributes:
            # we already have the list of attributes to show
            shown = shownAttributes;  hidden = []
            if shownAttributes != None:
                for attr in data.domain:
                    if attr.name not in shown: hidden.append(attr.name)
            for attr in shown:
                if self.attributeReverse[attr]: self.shownAttribsLB.insertItem(attr + " -")
                else:                           self.shownAttribsLB.insertItem(attr + " +")
            for attr in hidden:
                self.attributeReverse[attr] = 0
                self.hiddenAttribsLB.insertItem(attr + " +")
        else:
            for attr in data.domain.attributes[:10]:
                if self.attributeReverse[attr.name]: self.shownAttribsLB.insertItem(attr.name + " -")
                else:                                self.shownAttribsLB.insertItem(attr.name + " +")
            if len(data.domain.attributes) > 10:
                for attr in data.domain.attributes[10:]:
                    self.attributeReverse[attr.name] = 0
                    self.hiddenAttribsLB.insertItem(attr.name + " +")
            if data.domain.classVar:
                if self.attributeReverse[attr.name]: self.hiddenAttribsLB.insertItem(data.domain.classVar.name + " -")
                else:                                self.hiddenAttribsLB.insertItem(data.domain.classVar.name + " +")
                
        self.sendShownAttributes()
    
    ##############################################
    
    
    # ###### CDATA signal ################################
    # receive new data and update all fields
    def cdata(self, data, keepMinMaxVals = 0):
        if data:
            name = getattr(data, "name", "")
            data = orange.Preprocessor_dropMissingClasses(data)
            data.name = name
        if self.data != None and data != None and self.data.checksum() == data.checksum(): return    # check if the new data set is the same as the old one
        
        exData = self.data
        self.data = data
        self.graph.setData(self.data, keepMinMaxVals)
        self.optimizationDlg.setData(data)

        if not (data and exData and str(exData.domain.attributes) == str(data.domain.attributes)):    # preserve attribute choice if the domain is the same
            self.attributeReverse = {}
            if data:
                for attr in data.domain: self.attributeReverse[attr.name] = 0   # set reverse parameter to 0
            self.setShownAttributeList(data, self.attributeSelectionList)
            
        self.updateGraph()
        self.sendSelections()

    ####### SELECTION signal ################################
    # receive info about which attributes to show
    def attributeSelection(self, attributeSelectionList):
        self.attributeSelectionList = attributeSelectionList
        if self.data and attributeSelectionList:
            domain = [attr.name for attr in self.data.domain]
            for attr in attributeSelectionList:
                if attr not in domain or not self.attributeReverse.has_key(attr): return  # this attribute list belongs to a new dataset that has not come yet

            self.setShownAttributeList(self.data, attributeSelectionList)
            self.attributeSelectionList = None
            self.selectionChanged()
    
        self.updateGraph()

    # #########################
    # POLYVIZ EVENTS
    # #########################
    def updateValues(self):
        self.graph.setLineLength(self.lineLength)
        self.updateGraph()
    
    def setJitteringSize(self):
        self.graph.setData(self.data)
        self.updateGraph()

    def setGlobalValueScaling(self):
        self.graph.setData(self.data)
        self.updateGraph()

    def selectionChanged(self):
        if self.autoSendSelection:
            self.zoomSelectToolbar.buttonSendSelections.setEnabled(0)
            self.sendSelections()
        else:
            self.zoomSelectToolbar.buttonSendSelections.setEnabled(1)

    def setGraphCanvasColor(self):
        newColor = QColorDialog.getColor(QColor(self.graphCanvasColor))
        if newColor.isValid():
            self.graphCanvasColor = str(newColor.name())
            self.graph.setCanvasColor(QColor(newColor))


#test widget appearance
if __name__=="__main__":
    a=QApplication(sys.argv)
    ow=OWPolyviz()
    a.setMainWidget(ow)
    ow.show()
    a.exec_loop()

    #save settings 
    ow.saveSettings()
