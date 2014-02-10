import os
import unittest
from __main__ import vtk, qt, ctk, slicer

#
# Freehand3DUltrasound
#

class Freehand3DUltrasound:
  def __init__(self, parent):
    parent.title = "Freehand 3D Ultrasound" # TODO make this more human readable by adding spaces
    parent.categories = ["Examples"]
    parent.dependencies = []
    parent.contributors = ["Alireza Mehrtash (SPL, BWH)"] # replace with "Firstname Lastname (Org)"
    parent.helpText = """
    A module for recording tracked ultrasound and freehand 3D reconstruction.
    """
    parent.acknowledgementText = """
   . 
""" # replace with organization, grant and thanks.
    self.parent = parent

    # Add this test to the SelfTest module's list for discovery when the module
    # is created.  Since this module may be discovered before SelfTests itself,
    # create the list if it doesn't already exist.
    try:
      slicer.selfTests
    except AttributeError:
      slicer.selfTests = {}
    slicer.selfTests['Freehand3DUltrasound'] = self.runTest

  def runTest(self):
    tester = Freehand3DUltrasoundTest()
    tester.runTest()

#
# qFreehand3DUltrasoundWidget
#

class Freehand3DUltrasoundWidget:
  def __init__(self, parent = None):
    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
    else:
      self.parent = parent
    self.layout = self.parent.layout()
    if not parent:
      self.setup()
      self.parent.show()

    self.scene = slicer.mrmlScene
    # Module's Path
    self.freehand3DUltrasoundDirectoryPath = slicer.modules.freehand3dultrasound.path.replace("Freehand3DUltrasound.py","")

    beamModelPath = self.freehand3DUltrasoundDirectoryPath+"Resources/Models/"+"beam-model3.stl"
    successfulLoad = slicer.util.loadModel(beamModelPath)
    if successfulLoad == True:
      print 'loaded'

    nodes = self.scene.GetNodesByName('beam-model3') 
    n = nodes.GetNumberOfItems()
    for i in xrange(n):
      self.beamModelTemplateNode = nodes.GetItemAsObject(i)
    self.beamModelTemplateNode.SetDisplayVisibility(False)
    displayNode = self.beamModelTemplateNode.GetDisplayNode()
    displayNode.SetColor(1,1,0)

    self.recordedTransformNodes = []
    self.beamModelNodes = []
    self.beamModelDisplayNodes = []
    self.transformNode = None
    self.transformNodeObserverTag = None
    self.transformObserverTag= None    
    self.transform = None
    # Timer for connection status icon
    self.statusTimer = qt.QTimer()
    self.statusTimer.setInterval(100)
    self.statusTimer.connect('timeout()', self.changeImageTrackerIcon)
    self.recordBeanModelTimer = qt.QTimer()
    self.recordBeanModelTimer.setInterval(200)
    self.recordBeanModelTimer.connect('timeout()', self.recordBeamModel)

  def setup(self):
    # Instantiate and connect widgets ...

    #
    # Reload and Test area
    #
    reloadCollapsibleButton = ctk.ctkCollapsibleButton()
    reloadCollapsibleButton.text = "Reload && Test"
    self.layout.addWidget(reloadCollapsibleButton)
    reloadFormLayout = qt.QFormLayout(reloadCollapsibleButton)

    # reload button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadButton = qt.QPushButton("Reload")
    self.reloadButton.toolTip = "Reload this module."
    self.reloadButton.name = "Freehand3DUltrasound Reload"
    reloadFormLayout.addWidget(self.reloadButton)
    self.reloadButton.connect('clicked()', self.onReload)

    # reload and test button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadAndTestButton = qt.QPushButton("Reload and Test")
    self.reloadAndTestButton.toolTip = "Reload this module and then run the self tests."
    reloadFormLayout.addWidget(self.reloadAndTestButton)
    self.reloadAndTestButton.connect('clicked()', self.onReloadAndTest)
 
    # IGTLink Connector
    connectorCollapsibleButton = ctk.ctkCollapsibleButton()
    connectorCollapsibleButton.text = "OpenIGTLink Settings"
    self.layout.addWidget(connectorCollapsibleButton)    
    self.parametersVBoxLayout = qt.QVBoxLayout(connectorCollapsibleButton)    
    self.connectorWidget = qt.QWidget()
    self.parametersVBoxLayout.addWidget(self.connectorWidget)
    self.connectorLayout = qt.QFormLayout(self.connectorWidget)    
    
    self.linkInputSelector = slicer.qMRMLNodeComboBox()
    self.linkInputSelector.nodeTypes = ( ("vtkMRMLIGTLConnectorNode"), "" )
    self.linkInputSelector.selectNodeUponCreation = True
    self.linkInputSelector.addEnabled = True 
    self.linkInputSelector.removeEnabled = True
    self.linkInputSelector.noneEnabled = False
    self.linkInputSelector.showHidden = False
    self.linkInputSelector.showChildNodeTypes = False
    self.linkInputSelector.setMRMLScene( slicer.mrmlScene )
    self.linkInputSelector.setToolTip( "Pick connector node" )
    self.connectorLayout.addRow("PlusServer Connector: ", self.linkInputSelector)    

    self.igtLinkWidget = qt.QWidget()
    self.parametersVBoxLayout.addWidget(self.igtLinkWidget)
    self.igtLinkHBoxLayout = qt.QHBoxLayout(self.igtLinkWidget)
    self.hostNameLabel = qt.QLabel("Host Name:")
    self.igtLinkHBoxLayout.addWidget(self.hostNameLabel)
    self.hostNameLineEdit = qt.QLineEdit("localhost")
    self.igtLinkHBoxLayout.addWidget(self.hostNameLineEdit)
    self.portLabel = qt.QLabel(" Port:")
    self.igtLinkHBoxLayout.addWidget(self.portLabel)
    self.portLineEdit = qt.QLineEdit("18944")
    self.portLineEdit.setMaximumWidth(60)
    self.igtLinkHBoxLayout.addWidget(self.portLineEdit)
    self.statusLabel = qt.QLabel(" Active:")
    self.igtLinkHBoxLayout.addWidget(self.statusLabel)
    self.linkStatusCheckBox= qt.QCheckBox(" ")
    self.igtLinkHBoxLayout.addWidget(self.linkStatusCheckBox)

    #
    # Reconstruction Area
    #
    reconstructionCollapsibleButton = ctk.ctkCollapsibleButton()
    reconstructionCollapsibleButton.text = "Record and Reconstruction"
    self.layout.addWidget(reconstructionCollapsibleButton)

    # Layout within the dummy collapsible button
    reconstructionVBoxLayout = qt.QVBoxLayout(reconstructionCollapsibleButton)
    
    # Input Tracker node selector
    #
    inputImageTrackerWidget = qt.QWidget()
    reconstructionVBoxLayout.addWidget(inputImageTrackerWidget)
    inputImageTrackerQFormLayout = qt.QFormLayout(inputImageTrackerWidget)
    
    self.inputImageTrackerNodeSelector = slicer.qMRMLNodeComboBox()
    self.inputImageTrackerNodeSelector.nodeTypes = ['vtkMRMLLinearTransformNode']
    self.inputImageTrackerNodeSelector.selectNodeUponCreation = True
    self.inputImageTrackerNodeSelector.addEnabled = False
    self.inputImageTrackerNodeSelector.removeEnabled = False
    self.inputImageTrackerNodeSelector.noneEnabled = True
    self.inputImageTrackerNodeSelector.showHidden = False
    self.inputImageTrackerNodeSelector.showChildNodeTypes = False
    self.inputImageTrackerNodeSelector.setMRMLScene( slicer.mrmlScene )
    self.inputImageTrackerNodeSelector.objectName = 'inputImageTrackerNodeSelector'
    self.inputImageTrackerNodeSelector.toolTip = "Select the tracker linear transform node."
    #inputImageTrackerNodeSelector.connect('currentNodeChanged(bool)', self.enableOrDisableCreateButton)
    inputImageTrackerQFormLayout.addRow( 'Image Transform Node:',self.inputImageTrackerNodeSelector)
    #self.parent.connect('mrmlSceneChanged(vtkMRMLScene*)', inputImageTrackerNodeSelector, 'setMRMLScene(vtkMRMLScene*)')

    #
    # ROI Node Selector
    #
    self.inputROINodeSelector = slicer.qMRMLNodeComboBox()
    self.inputROINodeSelector.enabled = True
    self.inputROINodeSelector.addEnabled = True
    self.inputROINodeSelector.removeEnabled = True
    self.inputROINodeSelector.setMRMLScene( slicer.mrmlScene)
    self.inputROINodeSelector.nodeTypes = ['vtkMRMLAnnotationROINode']
    inputImageTrackerQFormLayout.addRow( 'Reconstruction ROI:',self.inputROINodeSelector)
    #
    # Icons 
    #
    self.statusRedIcon = qt.QIcon(self.freehand3DUltrasoundDirectoryPath+'/Resources/Icons/icon_DotRed.png')
    self.statusGreenIcon = qt.QIcon(self.freehand3DUltrasoundDirectoryPath+'/Resources/Icons/icon_DotGreen.png')
    self.connectIcon = qt.QIcon(self.freehand3DUltrasoundDirectoryPath+'/Resources/Icons/connect.png')
    self.disconnectIcon = qt.QIcon(self.freehand3DUltrasoundDirectoryPath+'/Resources/Icons/disconnect.png')
    self.recordIcon = qt.QIcon(self.freehand3DUltrasoundDirectoryPath+'/Resources/Icons/icon_Record.png')
    self.pauseIcon = qt.QIcon(self.freehand3DUltrasoundDirectoryPath+'/Resources/Icons/icon_pause.png')
    self.stopIcon = qt.QIcon(self.freehand3DUltrasoundDirectoryPath+'/Resources/Icons/icon_stop.png')
    self.snapshotIcon = qt.QIcon(self.freehand3DUltrasoundDirectoryPath+'/Resources/Icons/snapshot.png')
    self.deleteIcon= qt.QIcon(self.freehand3DUltrasoundDirectoryPath+'/Resources/Icons/delete.png')
    
    #
    # reconstruction and recording buttons
    self.recordAndReconstructionWidget = qt.QWidget()
    self.recordAndReconstructionWidget.enabled = False
    reconstructionVBoxLayout.addWidget(self.recordAndReconstructionWidget)
    recordAndReconstructionHBoxLayout = qt.QHBoxLayout(self.recordAndReconstructionWidget)
     
    self.startButton = qt.QPushButton("")
    buttonSize = 35 
    iconSize = qt.QSize(25,25)
    #self.startButton.toolTip = "Tracker Status"
    self.startButton.enabled = True 
    self.startButton.setIcon(self.recordIcon)
    self.startButton.checkable = True
    self.startButton.setMinimumHeight(buttonSize)
    self.startButton.setIconSize(iconSize)
    self.startButton.setMinimumWidth(buttonSize)
    self.startButton.setMaximumWidth(buttonSize)
    recordAndReconstructionHBoxLayout.addWidget(self.startButton)
  
    self.pauseButton = qt.QPushButton("")
    #self.pauseButton.toolTip = "Tracker Status"
    self.pauseButton.enabled = False 
    self.pauseButton.checkable = True
    self.pauseButton.setIcon(self.pauseIcon)
    self.pauseButton.setMinimumHeight(buttonSize)
    self.pauseButton.setIconSize(iconSize)
    self.pauseButton.setMinimumWidth(buttonSize)
    self.pauseButton.setMaximumWidth(buttonSize)
    recordAndReconstructionHBoxLayout.addWidget(self.pauseButton)       
 
    self.snapshotButton = qt.QPushButton("")
    #self.snapshotButton.toolTip = "Tracker Status"
    self.snapshotButton.enabled = False 
    self.snapshotButton.setIcon(self.snapshotIcon)
    recordAndReconstructionHBoxLayout.addWidget(self.snapshotButton)
    self.snapshotButton.setMinimumHeight(buttonSize)
    self.snapshotButton.setIconSize(iconSize)
    self.snapshotButton.setMinimumWidth(buttonSize)
    self.snapshotButton.setMaximumWidth(buttonSize)
 
    self.deleteButton = qt.QPushButton("")
    #self.deleteButton.toolTip = "Tracker Status"
    self.deleteButton.enabled = False 
    self.deleteButton.setIcon(self.deleteIcon)
    self.deleteButton.setMinimumHeight(buttonSize)
    self.deleteButton.setIconSize(iconSize)
    self.deleteButton.setMinimumWidth(buttonSize)
    self.deleteButton.setMaximumWidth(buttonSize)
    recordAndReconstructionHBoxLayout.addWidget(self.deleteButton)
    #recordAndReconstructionHBoxLayout.addStretch(1)

    self.statusButton = qt.QPushButton("")
    #self.startButton.toolTip = "Tracker Status"
    self.statusButton.enabled = False 
    self.statusButton.setIcon(self.disconnectIcon)
    self.statusButton.setIconSize(iconSize)
    self.statusButton.setMinimumHeight(buttonSize)
    self.statusButton.setMaximumWidth(buttonSize)
    self.statusButton.setMinimumWidth(buttonSize)
    recordAndReconstructionHBoxLayout.addWidget(self.statusButton)

    #
    # Display Area
    #
    displayCollapsibleButton = ctk.ctkCollapsibleButton()
    displayCollapsibleButton.text = "Display"
    self.layout.addWidget(displayCollapsibleButton)

    # Layout within the dummy collapsible button
    displayVBoxLayout = qt.QVBoxLayout(displayCollapsibleButton)
   
    volumesWidget = qt.QWidget()
    displayVBoxLayout.addWidget(volumesWidget)
    volumesFormLayout = qt.QFormLayout(volumesWidget)
    #
    # base volume node selector 
    #
    self.baseVolumeNodeSelector = slicer.qMRMLNodeComboBox()
    self.baseVolumeNodeSelector.setMRMLScene( slicer.mrmlScene)
    self.baseVolumeNodeSelector.nodeTypes = ['vtkMRMLScalarVolumeNode']
    volumesFormLayout.addRow( 'Base Volume (MR/CT):',self.baseVolumeNodeSelector)
    #
    # reconstructed volume node selector 
    #
    self.reconstructedVolumeNodeSelector = slicer.qMRMLNodeComboBox()
    self.reconstructedVolumeNodeSelector.setMRMLScene( slicer.mrmlScene)
    self.reconstructedVolumeNodeSelector.nodeTypes = ['vtkMRMLScalarVolumeNode']
    volumesFormLayout.addRow( 'Reconstructed Volume:',self.reconstructedVolumeNodeSelector)
    #
    # Pointer Transform Node Selector
    #
    self.pointerTransformNodeSelector = slicer.qMRMLNodeComboBox()
    self.pointerTransformNodeSelector.nodeTypes = ['vtkMRMLLinearTransformNode']
    self.pointerTransformNodeSelector.selectNodeUponCreation = True
    self.pointerTransformNodeSelector.addEnabled = False
    self.pointerTransformNodeSelector.removeEnabled = False
    self.pointerTransformNodeSelector.noneEnabled = True
    self.pointerTransformNodeSelector.showHidden = False
    self.pointerTransformNodeSelector.showChildNodeTypes = False
    self.pointerTransformNodeSelector.setMRMLScene( slicer.mrmlScene )
    self.pointerTransformNodeSelector.objectName = 'pointerTransformNodeSelector'
    self.pointerTransformNodeSelector.toolTip = "Select the tracker linear transform node."
    #pointerTransformNodeSelector.connect('currentNodeChanged(bool)', self.enableOrDisableCreateButton)
    volumesFormLayout.addRow( 'Pointer Transform Node:',self.pointerTransformNodeSelector)
    #self.parent.connect('mrmlSceneChanged(vtkMRMLScene*)', pointerTransformNodeSelector, 'setMRMLScene(vtkMRMLScene*)')

    #
    # Display Mode Group Buttons
    #
    displayModesWidget = qt.QWidget()
    displayVBoxLayout.addWidget(displayModesWidget)
    displayModesHBoxLayout = qt.QHBoxLayout(displayModesWidget)

    displayGroup = qt.QButtonGroup(volumesWidget)
    displayModeLabel = qt.QLabel("Display Mode: ")
    displayModesHBoxLayout.addWidget(displayModeLabel)
    self.mode1RadioButton = qt.QRadioButton("1- Recording")
    displayGroup.addButton(self.mode1RadioButton)
    self.mode2RadioButton = qt.QRadioButton("2- Pointer")
    displayGroup.addButton(self.mode2RadioButton)
    self.mode3RadioButton = qt.QRadioButton("3- Reslicing off")
    displayGroup.addButton(self.mode3RadioButton)
    displayModesHBoxLayout.addWidget(self.mode1RadioButton)
    displayModesHBoxLayout.addWidget(self.mode2RadioButton)
    displayModesHBoxLayout.addWidget(self.mode3RadioButton)
    displayModesHBoxLayout.addStretch(1)

    #
    # Settings Area
    #
    self.settingsCollapsibleButton = ctk.ctkCollapsibleButton()
    self.settingsCollapsibleButton.text = "Settings"
    self.layout.addWidget(self.settingsCollapsibleButton)

    # Layout within the dummy collapsible button
    settingsVBoxLayout = qt.QVBoxLayout(self.settingsCollapsibleButton)
   
    pathWidget = qt.QWidget()
    settingsVBoxLayout.addWidget(pathWidget)
    pathFormLayout = qt.QFormLayout(pathWidget)

    self.directoryButton = ctk.ctkDirectoryButton()
    pathFormLayout.addRow("Output Directory: ", self.directoryButton)
 
    #
    # Record and Reconstruction Parameters 
    #
    recordOptionsWidget = qt.QWidget()
    settingsVBoxLayout.addWidget(recordOptionsWidget)
    recordOptionsHBoxLayout = qt.QHBoxLayout(recordOptionsWidget)

    recordOptionsLabel = qt.QLabel("Options: ")
    recordOptionsHBoxLayout.addWidget(recordOptionsLabel)
    self.onlineReconstructionCheckBox = qt.QCheckBox("Online Reconstruction")
    self.onlineReconstructionCheckBox.checked = True
    self.recordTrackedFramesCheckBox = qt.QCheckBox("Record Tracked Frames")
    self.recordTrackedFramesCheckBox.checked = True
    self.probeSweepGuideCheckBox = qt.QCheckBox("Probe Sweep Guide")
    self.probeSweepGuideCheckBox.checked = True
    recordOptionsHBoxLayout.addWidget(self.onlineReconstructionCheckBox)
    recordOptionsHBoxLayout.addWidget(self.recordTrackedFramesCheckBox)
    recordOptionsHBoxLayout.addWidget(self.probeSweepGuideCheckBox)
    recordOptionsHBoxLayout.addStretch(1)
  
    # Add vertical spacer
    self.layout.addStretch(1)

    #
    # Connections
    #
    self.startButton.connect('toggled(bool)', self.onStartButton)
    self.inputImageTrackerNodeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.setTransformNode)
    self.deleteButton.connect('clicked(bool)',self.onDeleteButton)

  def cleanup(self):
    pass

  def setTransformNode(self, newTransformNode):
    """Allow to set the current Transform node. 
    Connected to signal 'currentNodeChanged()' emitted by Transform node selector."""
    
    #  Remove previous observer
    if self.transformNode and self.transformNodeObserverTag:
      self.transformNode.RemoveObserver(self.transformNodeObserverTag)
    if self.transform and self.transformObserverTag:
      self.transform.RemoveObserver(self.transformObserverTag)
    
    newTransform = None
    if newTransformNode:
      newTransform = vtk.vtkMatrix4x4()
      newTransformNode.GetMatrixTransformToWorld(newTransform)
      # Add TransformNode ModifiedEvent observer
      self.TransformNodeObserverTag = newTransformNode.AddObserver(slicer.vtkMRMLTransformNode.TransformModifiedEvent , self.onTransformNodeModified)
      # Add Transform ModifiedEvent observer
      self.transformObserverTag = newTransform.AddObserver(slicer.vtkMRMLTransformNode.TransformModifiedEvent, self.onTransformNodeModified)
      self.transformObserverTag = newTransform.AddObserver('TransformModifiedEvent', self.onTransformModified)
      
    self.transformNode = newTransformNode
    self.transform = newTransform
    
    # Update UI
    self.updateWidgetFromMRML()

  def updateWidgetFromMRML(self):

    if self.transform:
      
      self.statusButton.enabled = True
      self.recordAndReconstructionWidget.enabled = True
      self.statusButton.setIcon(self.connectIcon)
      self.statusTimer.start()
      #self.acquireTimer.setInterval(self.timeSlider.value)
      '''
      self.currentCoordinatesLabel.setText(newLabel)
      
      self.collectSignal = self.pointerDisplacementDistance > self.distanceSlider.value
        
      if (self.acquireButtonFlag and self.collectSignal ):
        self.pointsCounts += 1
        logic.acquirePoints(self.activeMarkupsNode,self.pointerPosition,self.nameBase,self.pointsCounts)
        self.recordedpoint = self.pointerPosition
      '''
    
    if self.transformNode:
      pass

  def onTransformModified(self, observer, eventid):
    self.updateWidgetFromMRML()
    
  def onTransformNodeModified(self, observer, eventid):
    self.updateWidgetFromMRML()

  def changeImageTrackerIcon(self):
    self.statusButton.setIcon(self.disconnectIcon)

  def onStartButton(self, toggled):
    if toggled == True:
      # Enable pause and snapshot buttons and disable settings collapsible button
      print 'toggled'
      self.pauseButton.enabled = True 
      self.deleteButton.enabled 
      self.snapshotButton.enabled = True 
      self.settingsCollapsibleButton.enabled = False
      # Send Record Command
      
      # Send Reconstruction Command

      # Send Probe Sweep Guide Command
      if self.probeSweepGuideCheckBox.checked:
        self.recordBeanModelTimer.start()
      #self.outputFileName = "TrackedImageSequence_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")+".mha"
      #self.fileNameBox.text = self.outputFileName
      #self.recordingButton.setText('Stop Recording')
      self.startButton.setIcon(self.stopIcon)
      #logic = PlusRemoteLogic()
      #self.lastCommandId = logic.startRecording(self.linkInputSelector.currentNode().GetID(),
      #self.captureIDBox.text, self.currentDirectory, self.outputFileName)
      #self.setTimer()
    else:
      # Disable pause and snapshot buttons and enable settings collapsible button
      self.pauseButton.enabled = False 
      self.snapshotButton.enabled = False 
      self.deleteButton.enabled = True
      self.settingsCollapsibleButton.enabled = True 
      self.startButton.setIcon(self.recordIcon)
      self.recordBeanModelTimer.stop()
      '''
      logic = PlusRemoteLogic()
      self.lastCommandId = logic.stopRecording(self.linkInputSelector.currentNode().GetID(), self.captureIDBox.text)
      self.setTimer()
      '''

  def recordBeamModel(self):

    # create a new transform with the current one
    # TODO: harden transform?
    # create a new transform node

    '''
    recordedTransformNode = slicer.vtkMRMLLinearTransformNode()
    recordedTransformNode.CopyWithoutModifiedEvent(self.transformNode)
    slicer.mrmlScene.AddNode(recordedTransformNode)
    recordedTransformName = recordedTransformNode.GetName() + str(len(self.recordedTransformNodes))
    recordedTransformNode.SetName(recordedTransformName)
    self.recordedTransformNodes.append(recordedTransformNode)
    print 'recorded transform', len(self.recordedTransformNodes)

    '''
    transformNode = self.transformNode
    transformMatrix = vtk.vtkMatrix4x4()
    transformNode.GetMatrixTransformToWorld(transformMatrix)
    # create a new model and apply the transform
    model = slicer.vtkMRMLModelNode()
    self.beamModelNodes.append(model)

    model.CopyWithoutModifiedEvent(self.beamModelTemplateNode)

    modelDisplay = slicer.vtkMRMLModelDisplayNode()
    modelDisplay.SetColor(1,1,0) # yellow
    modelDisplay.SetScene(self.scene)
    self.beamModelDisplayNodes.append(modelDisplay)
    self.scene.AddNode(modelDisplay)
    model.SetAndObserveDisplayNodeID(modelDisplay.GetID())
     
    # Add to scene
    modelDisplay.SetInputPolyData(model.GetPolyData())
    modelDisplay.SetSliceIntersectionVisibility(True)
    self.scene.AddNode(model)
    #model.ApplyTransformMatrix(transformMatrix)

  def onDeleteButton(self):
    for node in self.beamModelNodes:
      slicer.mrmlScene.RemoveNode(node)

    for node in self.beamModelDisplayNodes:
      slicer.mrmlScene.RemoveNode(node)

    self.beamModelNodes= []
    self.beamModelDisplayNodes = []
    self.deleteButton.enabled = False 

  def onReload(self,moduleName="Freehand3DUltrasound"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    globals()[moduleName] = slicer.util.reloadScriptedModule(moduleName)

  def onReloadAndTest(self,moduleName="Freehand3DUltrasound"):
    try:
      self.onReload()
      evalString = 'globals()["%s"].%sTest()' % (moduleName, moduleName)
      tester = eval(evalString)
      tester.runTest()
    except Exception, e:
      import traceback
      traceback.print_exc()
      qt.QMessageBox.warning(slicer.util.mainWindow(), 
          "Reload and Test", 'Exception!\n\n' + str(e) + "\n\nSee Python Console for Stack Trace")

#
# Freehand3DUltrasoundLogic
#

class Freehand3DUltrasoundLogic:
  """This class should implement all the actual 
  computation done by your module.  The interface 
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget
  """
  def __init__(self):
    pass


class Freehand3DUltrasoundTest(unittest.TestCase):
  """
  This is the test case for your scripted module.
  """

  def delayDisplay(self,message,msec=1000):
    """This utility method displays a small dialog and waits.
    This does two things: 1) it lets the event loop catch up
    to the state of the test so that rendering and widget updates
    have all taken place before the test continues and 2) it
    shows the user/developer/tester the state of the test
    so that we'll know when it breaks.
    """
    print(message)
    self.info = qt.QDialog()
    self.infoLayout = qt.QVBoxLayout()
    self.info.setLayout(self.infoLayout)
    self.label = qt.QLabel(message,self.info)
    self.infoLayout.addWidget(self.label)
    qt.QTimer.singleShot(msec, self.info.close)
    self.info.exec_()

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_Freehand3DUltrasound1()

  def test_Freehand3DUltrasound1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests sould exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
