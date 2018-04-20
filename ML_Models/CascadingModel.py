from ML_Models.UserMetrics import *
import numpy as np
from Utility.TagsDef import getUsers
import json
from ML_Models.XGBoostModel import XGBoostClassifier
from ML_Models.DNNModel import DNNCLassifier
from ML_Models.EnsembleModel import EnsembleClassifier
from sklearn.base import BaseEstimator,RegressorMixin
class CascadingModel(BaseEstimator,RegressorMixin):

    def initData(self):

        self.mymetric=TopKMetrics(tasktype=self.tasktype,testMode=True)
        self.subExpr=self.mymetric.subRank
        self.userIndex=getUsers(self.tasktype+"-test",mode=2)

        if self.verbose>0:
            print("model init for %d users"%len(self.userIndex),"%d tasks"%len(self.subExpr))

    def __init__(self,tasktype=None,topK=3,verbose=0,metaReg=1,metaSub=1,metaWin=1,
                 regThreshold=1,subThreshold=1,topDig=1):
        #meta-learners
        self.regModel=None
        self.subModel=None
        self.winModel=None
        self.availableModels={
            1:EnsembleClassifier,
            2:XGBoostClassifier,
            3:DNNCLassifier
        }
        self.metaReg=metaReg
        self.metaSub=metaSub
        self.metaWin=metaWin
        #parameters
        self.regThreshold=regThreshold
        self.subThreshold=subThreshold
        self.topDig=topDig

        #aux info
        self.verbose=verbose
        self.tasktype=tasktype
        self.initData()
        self.topK=topK
        self.name=tasktype+"rulePredictor"

        self.loadModel()
        self.bestScore=0
        self.setVerbose(self.verbose)

    def setVerbose(self,verbose):
        self.verbose=verbose
        self.regModel.verbose=self.verbose-1
        self.subModel.verbose=self.verbose-1
        self.winModel.verbose=self.verbose-1
        self.mymetric.verbose=verbose

    def loadModel(self):
        tasktype=self.tasktype

        self.regModel=self.availableModels[self.metaReg]()
        self.subModel=self.availableModels[self.metaSub]()
        self.winModel=self.availableModels[self.metaWin]()

        self.winModel.name=tasktype+"-classifierWin"

        if  "#" in tasktype:
            pos=tasktype.find("#")
            self.regModel.name=tasktype[:pos]+"-classifierReg"
            self.subModel.name=tasktype[:pos]+"-classifierSub"
        else:
            self.regModel.name=tasktype+"-classifierReg"
            self.subModel.name=tasktype+"-classifierSub"

        self.regModel.loadModel()
        self.subModel.loadModel()
        self.winModel.loadModel()
        if self.verbose>0:
            print("meta learner loaded",self.regModel,self.subModel,self.winModel)

    def score(self, data, y=None, sample_weight=None):
        Y=self.predict(data.testX,data.taskids)
        acc=self.mymetric.topKPossibleUsers(Y,data,self.topK)
        acc=np.mean(acc)
        return acc

    def fit(self,x,y=None):
        self.loadModel()

        return self

    def predict(self,X,taskids=None):

        if self.verbose>0:
            print("Cascading Model(%d,%d,%d) is predicting top %d for %d users,parameters are"%(
                self.metaReg,self.metaSub,self.metaWin,self.topK,len(self.userIndex)))
            print("regThreshold=%f, subThreshold=%f, DigThreshold=%f"%(self.regThreshold,self.subThreshold,
                  self.topDig))
            print()

        regY=self.regModel.predict(X)
        subY=self.subModel.predict(X)
        winY=self.winModel.predict(X)

        Y=np.zeros(shape=len(X))
        taskNum=len(X)//len(self.userIndex)
        topRN=int(self.regThreshold*len(self.userIndex))
        topSN=int(self.subThreshold*len(self.userIndex))
        topN=int(self.topDig*len(self.userIndex))

        for i in range(taskNum):
            left=i*len(self.userIndex)
            right=(i+1)*len(self.userIndex)
            taskid=taskids[left]
            topReg,_=self.mymetric.getTopKonPossibility(regY[left:right],topRN)
            topSub,_=self.mymetric.getTopKonPossibility(subY[left:right],topSN)
            selectedusers,_ =self.mymetric.getTopKonDIGRank(self.subExpr[taskid]["ranks"],topN)
            #print("topR%d"%len(topReg),topReg)
            #print("topS%d"%len(topSub),topSub)
            #print("topD%d"%len(selectedusers),selectedusers)
            for j in range(len(self.userIndex)):
                pos=i*len(self.userIndex)+j
                #reg

                if j not in topReg:
                    #count+=1
                    continue

                #sub
                #print(taskid,len(selectedusers),len(self.subExpr[taskid]["ranks"]),topN)
                if j not in topSub or j not in selectedusers:
                    #count+=1
                    continue
                #winner

                Y[pos]=winY[pos]
        #print("filtered %d in predict"%count)
        return Y

    def saveConf(self):
        params={"regThreshold":self.regThreshold,
                "subThreshold":self.subThreshold,
                "topDig":self.topDig,
                "metaReg":self.metaReg,"metaSub":self.metaSub,"metaWin":self.metaWin
                }

        with open("../data/saved_ML_models/MetaPredictor/"+self.name+"-top"+str(self.topK)+".json","w") as f:
            json.dump(params,f)

    def loadConf(self):
        with open("../data/saved_ML_models/MetaPredictor/"+self.name+"-top"+str(self.topK)+".json","r") as f:
                params=json.load(f)

        self.regThreshold=params["regThreshold"]
        self.subThreshold=params["subThreshold"]
        self.topDig=params["topDig"]
        self.metaReg=params["metaReg"]
        self.metaSub=params["metaSub"]
        self.metaWin=params["metaWin"]
