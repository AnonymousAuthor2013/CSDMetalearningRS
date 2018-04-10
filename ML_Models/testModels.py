from ML_Models.TraditionalModel import *
from ML_Models.CascadingModel import *
from ML_Models.DNNModel import *
from DataPrepare.TopcoderDataSet import *
from sklearn import metrics
import multiprocessing

def testRegClassification(tasktype,queue,model=TraditionalClassifier()):
    data=TopcoderReg(tasktype,testratio=0.2,validateratio=0.1)

    data.loadData()

    data.RegisterClassificationData()
    data.trainX,data.trainLabel=data.ReSampling(data.trainX,data.trainLabel)
    data.validateX,data.validateLabel=data.ReSampling(data.validateX,data.validateLabel)

    model.name=data.tasktype+"-classifier(Reg)"
    model.trainModel(data)
    model.saveModel()
    model.loadModel()
    Y_predict2=model.predict(data.testX)
    print("test score=%f"%(metrics.accuracy_score(data.testLabel,Y_predict2)))
    print("Confusion matrix ")
    print(metrics.confusion_matrix(data.testLabel,Y_predict2))
def testSubClassification(tasktype,queue,model=TraditionalClassifier()):
    data=TopcoderSub(tasktype,testratio=0.2,validateratio=0.1)

    data.loadData()

    data.SubmitClassificationData()
    data.trainX,data.trainLabel=data.ReSampling(data.trainX,data.trainLabel)
    data.validateX,data.validateLabel=data.ReSampling(data.validateX,data.validateLabel)

    model.name=data.tasktype+"-classifier(Reg)"
    model.trainModel(data)
    model.saveModel()
    model.loadModel()
    Y_predict2=model.predict(data.testX)
    print("test score=%f"%(metrics.accuracy_score(data.testLabel,Y_predict2)))
    print("Confusion matrix ")
    print(metrics.confusion_matrix(data.testLabel,Y_predict2))

def testWinClassification(tasktype,queue,model=TraditionalClassifier()):
    data=TopcoderWin(tasktype,testratio=0.2,validateratio=0.1)
    data.loadData()
    data.WinClassificationData()
    data.trainX,data.trainLabel=data.ReSampling(data.trainX,data.trainLabel)
    data.validateX,data.validateLabel=data.ReSampling(data.validateX,data.validateLabel)

    model.name=data.tasktype+"-classifier(Win)"
    model.trainModel(data)
    model.saveModel()
    model.loadModel()
    Y_predict2=model.predict(data.testX)
    print("test score=%f"%(metrics.accuracy_score(data.testLabel,Y_predict2)))
    print("Confusion matrix ")
    print(metrics.confusion_matrix(data.testLabel,Y_predict2))
    kacc=[data.tasktype]
    for k in (3,5,10,20):
        acc=topKAccuracyWithDIG(Y_predict2,data,k)
        acc=np.mean(acc)
        print(data.tasktype,"top %d"%k,acc)
        kacc=kacc+[acc]
    print()
    queue.put(kacc)

def testCascadingModel(tasktype,queue):
    data=TopcoderWin(tasktype,testratio=0.2,validateratio=0.1)
    data.loadData()
    data.WinClassificationData()
    data.trainX,data.trainLabel=data.ReSampling(data.trainX,data.trainLabel)
    data.validateX,data.validateLabel=data.ReSampling(data.validateX,data.validateLabel)

    model=CascadingModel()
    model.loadModel(tasktype)

    Y_predict2=model.predict(data.testX)
    print("test score=%f"%(metrics.accuracy_score(data.testLabel,Y_predict2)))
    print("Confusion matrix ")
    print(metrics.confusion_matrix(data.testLabel,Y_predict2))
    kacc=[data.tasktype]
    for k in (3,5,10,20):
        acc=topKAccuracyWithDIG(Y_predict2,data,k)
        acc=np.mean(acc)
        print(data.tasktype,"top %d"%k,acc)
        kacc=kacc+[acc]
    print()
    queue.put(kacc)



#test the performance
if __name__ == '__main__':
    testMethod={
        1:testRegClassification,
        2:testSubClassification,
        3:testWinClassification,
        4:testCascadingModel
    }
    selectedmethod=1

    # begin test
    from Utility import SelectedTaskTypes
    tasktypes=SelectedTaskTypes.loadTaskTypes()
    mode=1
    queue=multiprocessing.Queue()
    pool_processes=[]
    for t in tasktypes["keeped"]:
        if t !="Conceptualization":
            continue
        #testWinRankClassification(t)

        p=multiprocessing.Process(target=testMethod[selectedmethod],args=(t,queue))
        pool_processes.append(p)
        p.start()
        #p.join()
    for p in pool_processes:
        p.join()

    result=""
    while queue.empty()==False:
        data=queue.get()
        result=result+data[0]+" : %f"%data[1]
    with open("../data/runResults/rankPrediction.txt","w") as f:
        f.writelines(result)
