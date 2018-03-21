from DataPrepare.ConnectDB import *
import numpy as np
import pickle
import copy
import time
import gc
from DataPrepare.clusterTasks import onehotFeatures,showData,loadTaskVecData,Vectorizer
warnings.filterwarnings("ignore")

class Users:
    def __init__(self):
        self.loadData()

    def loadData(self):
        conn = ConnectDB()
        cur = conn.cursor()
        sqlcmd = 'select handle,memberage,skills,competitionNum,submissionNum,winNum from users'
        cur.execute(sqlcmd)
        dataset = cur.fetchall()
        self.name=[]
        self.memberage=[]
        self.skills=[]
        self.competitionNum=[]
        self.submissionNum=[]
        self.winNum=[]
        for data in dataset:
            if data[4]<1:
                #those have no submission hoistory is filtered out
                continue
            self.name.append(data[0])
            if data[1]<1:
                self.memberage.append(1)
            else:
                self.memberage.append(data[1])
            self.skills.append(data[2])
            self.competitionNum.append(data[3])
            self.submissionNum.append(data[4])
            self.winNum.append(data[5])
        self.name=np.array(self.name)
        self.skills=np.array(self.skills)
        self.memberage=np.log(self.memberage)
        self.competitionNum=np.array(self.competitionNum)
        self.submissionNum=np.array(self.submissionNum)
        self.winNum=np.array(self.winNum)

        print("users num=%d"%len(self.name))

    def getUsers(self):
        names=self.name
        return names

    def getInfo(self,username):
        index=np.where(self.name==username)[0]
        if len(index)>0:
            return (self.memberage[index][0],self.skills[index][0])
        else:
            return (None,None)

    def transformVec(self):
        n=len(self.name)
        X=np.concatenate((self.skills,np.reshape(self.memberage,newshape=(n,1))),axis=1)
        X=np.concatenate((X,np.reshape(self.winNum,newshape=(n,1))),axis=1)
        X=np.concatenate((X,np.reshape(self.competitionNum,newshape=(n,1))),axis=1)
        X=np.concatenate((X,np.reshape(self.submissionNum,newshape=(n,1))),axis=1)
        return X

class Registration:
    def __init__(self):
        self.loadData()

    def loadData(self):
        conn = ConnectDB()
        cur = conn.cursor()
        sqlcmd = 'select taskid, handle,regdate from registration where regdate<2500 order by regdate desc'
        cur.execute(sqlcmd)
        dataset = cur.fetchall()
        self.taskid=[]
        self.username=[]
        self.regdate=[]
        for data in dataset:
            self.taskid.append(data[0])
            self.username.append(data[1])
            if data[2]<1:
                self.regdate.append(1)
            else:
                self.regdate.append(data[2])
        self.taskid=np.array(self.taskid)
        self.username=np.array(self.username)

        self.regdate=np.log(np.array(self.regdate,dtype=np.int))
        print("registration num=%d"%len(dataset))
    def getUserHistory(self,username):

        indices=np.where(self.username==username)[0]
        if len(indices)==0:
            return (np.array([]),np.array([]))

        ids=self.taskid[indices]
        date=self.regdate[indices]
        return [ids,date]

    def getUsers(self,taskid):
        indices=np.where(self.taskid==taskid)[0]
        if len(indices)==0:
            return None
        #print(indices)
        #print(len(self.username))
        taskUsers=self.username[indices]
        return taskUsers
    def setActiveTaskUser(self,taskids=None,usernames=None):

        if taskids is not None:
            activeID = []
            activeName = []
            activeDate = []
            for id in taskids:
                indices=np.where(self.taskid==id)[0]
                if len(indices)==0:
                    continue
                else:
                    ids=self.taskid[indices].tolist()
                    dates=self.regdate[indices].tolist()
                    names=self.username[indices].tolist()
                    activeID=activeID+ids
                    activeName=activeName+names
                    activeDate=activeDate+dates

            self.taskid=np.array(activeID)
            self.username=np.array(activeName)
            self.regdate=np.array(activeDate)

        if usernames is not None:
            activeID = []
            activeName = []
            activeDate = []
            for name in usernames:
                indices=np.where(self.username==name)[0]
                if len(indices)==0:
                    continue
                else:
                    ids = self.taskid[indices].tolist()
                    dates = self.regdate[indices].tolist()
                    names = self.username[indices].tolist()
                    activeID = activeID + ids
                    activeName = activeName + names
                    activeDate = activeDate + dates
            self.taskid = np.array(activeID)
            self.username = np.array(activeName)
            self.regdate = np.array(activeDate)
        #data active
        print("active reg data set size=",len(self.taskid))

class Submission:
    def __init__(self):
        self.loadData()
    def loadData(self):
        conn = ConnectDB()
        cur = conn.cursor()
        sqlcmd = 'select taskid,handle,subnum,submitdate,score from submission where submitdate<2500 order by submitdate desc'
        cur.execute(sqlcmd)
        dataset = cur.fetchall()
        self.taskid=[]
        self.username=[]
        self.subnum=[]
        self.subdate=[]
        self.score=[]

        for data in dataset:
            self.taskid.append(data[0])
            self.username.append(data[1])
            self.subnum.append(data[2])
            if data[3]>4200:
                self.subdate.append(4200)
            elif data[3]<1:
                self.subdate.append(1)
            else:
                self.subdate.append(data[3])
            if data[4] is not None:
                self.score.append(data[4])
            else:
                self.score.append(0)

        self.taskid=np.array(self.taskid)
        self.username=np.array(self.username)
        self.subnum=np.array(self.subnum)
        self.subdate=np.log(np.array(self.subdate,dtype=np.int))

        self.score=np.array(self.score)
        self.finalrank =np.zeros(shape=len(self.taskid))
        #assign ranking for each task
        taskset=set(self.taskid)
        for id in taskset:
            indices=np.where(self.taskid==id)[0]
            scores=copy.deepcopy(self.score[indices])
            count=0
            step=0
            #print(len(indices),scores)
            while count<10 and step<len(scores):
                step+=1
                max_score=np.max(scores)
                indices1=np.where(scores>=max_score)[0]
                #print(max_score, count,indices1)
                scores[indices1]=-1
                indices2=indices1+indices[0]
                self.finalrank[indices2]=count
                count += len(indices1)

        print("sub num=%d"%len(self.taskid))
    def getResultOfSubmit(self,username,taskid):
        indices=np.where(self.username==username)[0]
        if len(indices)==0:
            return None
        indices1=np.where(self.taskid[indices]==taskid)[0]
        if len(indices1)==0:
            return None
        indices=indices1+indices[0]
        return [self.subnum[indices][0],self.finalrank[indices][0]]
    def getUserHistory(self,username):

        indices=np.where(self.username==username)[0]
        if len(indices)==0:
            return (np.array([]),np.array([]),np.array([]),np.array([]),np.array([]))

        ids=self.taskid[indices]
        subnum=self.subnum[indices]
        date=self.subdate[indices]
        score=self.score[indices]
        rank=self.finalrank[indices]
        return (ids,subnum,date,score,rank)

    def setActiveTaskUser(self, taskids=None, usernames=None):
        #set submission entry related with given taskids and usernames
        if taskids is not None:
            activeID = []
            activeName = []
            activeDate = []
            activeNum=[]
            activeScore=[]
            activeRank=[]

            for id in taskids:
                indices = np.where(self.taskid == id)[0]
                if len(indices) == 0:
                    continue
                else:
                    ids = self.taskid[indices].tolist()
                    dates = self.subdate[indices].tolist()
                    names = self.username[indices].tolist()
                    nums=self.subnum[indices].tolist()
                    scores=self.score[indices].tolist()
                    ranks=self.finalrank[indices].tolist()

                    activeID = activeID + ids
                    activeName = activeName + names
                    activeDate = activeDate + dates
                    activeNum=activeNum+nums
                    activeScore=activeScore+scores
                    activeRank=activeRank+ranks

            self.taskid = np.array(activeID)
            self.username = np.array(activeName)
            self.subdate = np.array(activeDate)
            self.subnum=np.array(activeNum)
            self.score=np.array(activeScore)
            self.finalrank=np.array(activeRank)

        if usernames is not None:
            activeID = []
            activeName = []
            activeDate = []
            activeNum = []
            activeScore = []
            activeRank = []
            for name in usernames:
                indices = np.where(self.username == name)[0]
                if len(indices) == 0:
                    continue
                else:
                    #print(self.taskid)
                    #print(indices)
                    ids = self.taskid[indices].tolist()
                    dates = self.subdate[indices].tolist()
                    names = self.username[indices].tolist()
                    nums = self.subnum[indices].tolist()
                    scores = self.score[indices].tolist()
                    ranks = self.finalrank[indices].tolist()

                    activeID = activeID + ids
                    activeName = activeName + names
                    activeDate = activeDate + dates
                    activeNum = activeNum + nums
                    activeScore = activeScore + scores
                    activeRank = activeRank + ranks

            self.taskid = np.array(activeID)
            self.username = np.array(activeName)
            self.subdate = np.array(activeDate)
            self.subnum = np.array(activeNum)
            self.score = np.array(activeScore)
            self.finalrank = np.array(activeRank)

        # data active
        print("active sub data set size=", len(self.taskid))

class Tasks:
    def __init__(self):
        self.taskIDs=[]
        self.postingdate=[]
        self.loadData()
    def loadData(self):
        conn = ConnectDB()
        cur = conn.cursor()
        sqlcmd="select taskid, postingdate from task where postingdate <=600 and postingdate>=0 order by postingDate asc;"
        cur.execute(sqlcmd)
        dataset = cur.fetchall()
        for data in dataset:
            self.taskIDs.append(data[0])
            self.postingdate.append(data[1])

        self.taskIDs=np.array(self.taskIDs)
        self.postingdate=np.log(np.array(self.postingdate,dtype=np.int))
        print("task item size=",len(self.taskIDs))


class DataInstances:
    def __init__(self,regdata,subdata,userdata):
        self.regdata=regdata
        self.subdata=subdata
        self.userdata=userdata

    def setLocality(self,taskIDs=None):

        self.activeReg=[]
        if taskIDs is None:
            self.localtasks=None
            for i in range(len(self.regdata.taskid)):
                self.activeReg.append((self.regdata.taskid[i],self.regdata.username[i],self.regdata.regdate[i]))

        else:
            self.localtasks=taskIDs
            taskIDs=np.array(taskIDs,dtype=np.int64)
            for i in range(len(self.regdata.taskid)):
                indices=np.where(taskIDs==self.regdata.taskid[i])[0]
                if len(indices)>0:
                    self.activeReg.append((self.regdata.taskid[i],self.regdata.username[i],self.regdata.regdate[i]))
        self.activeReg.reverse()
        print("set locality: regtasks size=%d" % (len(self.activeReg)))

    def loadActiveUsers(self):
        print("loading history of active users")
        with open("../data/Instances/UserHistory/activeUsers2500.data", "rb") as f:
            act_userData = pickle.load(f)

        self.act_userData=act_userData
        self.regdata.setActiveTaskUser(usernames=act_userData.keys())
        self.subdata.setActiveTaskUser(usernames=act_userData.keys())


    def createRegInstances(self,choice=1):
        tasks = []
        users = []
        usernames = []
        taskids = []
        dates = []
        regists = []

        taskIndex=Tasks()
        missingtask = 0
        missinguser = 0

        t0 = time.time()
        with open("../data/clusterResult/taskVec" + str(choice) + ".data", "rb") as f:
            taskdata = pickle.load(f)
            ids = taskdata["taskids"]
            X = taskdata["tasks"]
            print("task vec data size=%d"%(len(ids)),taskdata["size"])
            taskdata = {}
            for i in range(len(ids)):
                taskdata[ids[i]] = X[i]


        userData=self.act_userData
        print("construct Regist instances with %d tasks and %d users" % (len(taskIndex.taskIDs), len(userData.keys())))

        begin=0
        end=0

        for index in range(0,len(taskIndex.taskIDs)):
            end+=1
            if (index+1)%10000==0:
                print(index+1,"of",len(taskIndex.taskIDs),"current size=%d"%(len(taskids)),"in %ds"%(time.time()-t0))
                t0=time.time()

            id=taskIndex.taskIDs[index]
            date=taskIndex.postingdate[index]

            if id not in taskdata.keys():
                missingtask += 1
                continue
            task = taskdata[id]

            taskUsers=self.regdata.getUsers(id)
            if taskUsers is None:
                taskUsers=[]

            for name in userData.keys():
                tenure, skills = self.userdata.getInfo(name)
                if tenure is None:
                    #no such user
                    continue

                regtasks = userData[name]["regtasks"]
                while len(regtasks[0])>0 and regtasks[1][len(regtasks[1])-1]<date:
                    for l in range(len(regtasks)):
                        regtasks[l]=np.delete(regtasks[l],len(regtasks[l])-1,axis=0)
                userData[name]["regtasks"]=regtasks

                if len(regtasks[0])==0:
                    missinguser += 1
                    continue

                subtasks = userData[name]["subtasks"]
                while len(subtasks[0])>0 and subtasks[2][len(subtasks[2])-1]<date:
                    for l in range(len(subtasks)):
                        subtasks[l]=np.delete(subtasks[l],len(subtasks[l])-1,axis=0)
                userData[name]["subtasks"]=subtasks

                #reg history info
                regID, regDate = regtasks[0], regtasks[1]
                participate_recency = regDate[len(regDate) - 1]
                date_interval = max(1, regDate[0] - regDate[len(regDate) - 1])
                participate_frequency = len(regID) / date_interval

                #sub history info
                if len(subtasks[0])==0:
                    commit_recency = -1
                    commit_frequency = 0
                    last_perfromance = 0
                    win_recency = -1
                    win_frequency = 0

                else:
                    subID, subNum, subDate, subScore, subrank = subtasks[0], subtasks[1], subtasks[2], subtasks[3], \
                                                                subtasks[4]
                    commit_recency = subDate[len(subDate) - 1]
                    commit_frequency = np.sum(subNum) / date_interval
                    last_perfromance = subScore[len(subScore) - 1]
                    win_recency = -1
                    for i in range(1, len(subID) + 1):
                        if subrank[-i] == 0:
                            win_recency = subDate[-i]
                    win_indices = np.where(subrank == 0)[0]
                    if len(win_indices) > 0:
                        win_frequency = len(win_indices) / date_interval
                    else:
                        win_frequency = 0


                user = [tenure, participate_recency, participate_frequency, commit_recency, commit_frequency,
                        win_recency, win_frequency, last_perfromance] + skills.tolist()

                usernames.append(name)
                taskids.append(id)
                users.append(user)
                tasks.append(task)
                dates.append(date)

                if name in taskUsers:
                    regists.append(1)
                else:
                    regists.append(0)


            if len(taskids)>1000000:
                print("saving data")
                data = {}
                data["usernames"] = usernames
                data["taskids"] = taskids
                data["tasks"] = tasks
                data["users"] = users
                data["dates"] = dates
                data["regists"]=regists

                with open("../data/Instances/regsdata/task_userReg" + str(choice) + ".data"+str(begin)+"_"+str(end), "wb") as f:

                    pickle.dump(data, f)
                    begin=end

                data={}
                tasks = []
                users = []
                usernames = []
                taskids = []
                dates = []
                regists = []
                gc.collect()

        data = {}
        data["usernames"] = usernames
        data["taskids"] = taskids
        data["tasks"] = tasks
        data["users"] = users
        data["dates"] = dates
        data["regists"]=regists

        print("missing task", missingtask, "missing user", missinguser, "instances size", len(taskids))
        print()

        print("saving data")

        with open("../data/Instances/regsdata/task_userReg" + str(choice) + ".data"+str(begin)+"_"+str(end), "wb") as f:
            pickle.dump(data, f)

        return data

    def createRegisteredInstances(self,choice=1):

        tasks=[]
        users=[]
        usernames = []
        taskids = []
        dates = []
        submits = []
        ranks = []

        with open("../data/clusterResult/taskVec"+str(choice)+".data","rb") as f:
            taskdata=pickle.load(f)
            ids=taskdata["taskids"]
            X=taskdata["tasks"]
            print("task size=%d"%(len(ids)),taskdata["size"])
            taskdata={}
            for i in range(len(ids)):
                taskdata[ids[i]]=X[i]

        userData=self.act_userData

        print("construct Registered instances with %d tasks and %d users" % (len(taskdata), len(userData.keys())))

        missingtask=0
        missinguser=0

        t0=time.time()

        for index in range(len(self.activeReg)):
            if (index+1)%10000==0:
                print(index+1,"of",len(self.activeReg),"current size=%d"%(len(taskids)),"in %ds"%(time.time()-t0))
                t0=time.time()

            id, name, date=self.activeReg[index]

            if name not in userData.keys():
                #no history
                continue
            if id not in taskdata.keys():
                #no task data
                missingtask+=1
                continue

            tenure, skills = self.userdata.getInfo(name)
            if tenure is None:
                #no such user in user data
                continue

            # task data of id
            task = taskdata[id]

            #get reg and sub history before date for user:name
            regtasks = userData[name]["regtasks"]
            while len(regtasks[0]) > 0 and regtasks[1][len(regtasks[1]) - 1] < date:
                for l in range(len(regtasks)):
                    regtasks[l] = np.delete(regtasks[l], len(regtasks[l]) - 1, axis=0)
            userData[name]["regtasks"] = regtasks

            if len(regtasks[0]) == 0:
                missinguser += 1
                continue


            subtasks = userData[name]["subtasks"]
            while len(subtasks[0]) > 0 and subtasks[2][len(subtasks[2]) - 1] < date:
                for l in range(len(subtasks)):
                    subtasks[l] = np.delete(subtasks[l], len(subtasks[l]) - 1, axis=0)
            userData[name]["subtasks"] = subtasks

            #print("reg and sub history of",name,len(regtasks[0]),len(subtasks[0]))

            # reg history info
            regID, regDate = regtasks[0], regtasks[1]
            participate_recency = regDate[len(regDate) - 1]
            date_interval = max(1, regDate[0] - regDate[len(regDate) - 1])
            participate_frequency = len(regID) / date_interval

            # sub history info
            if len(subtasks[0]) == 0:
                commit_recency = -1
                commit_frequency = 0
                last_perfromance = 0
                win_recency = -1
                win_frequency = 0

            else:
                subID, subNum, subDate, subScore, subrank = subtasks[0], subtasks[1], subtasks[2], subtasks[3], \
                                                            subtasks[4]
                commit_recency = subDate[len(subDate) - 1]
                commit_frequency = np.sum(subNum) / date_interval
                last_perfromance = subScore[len(subScore) - 1]
                win_recency = -1
                for i in range(1, len(subID) + 1):
                    if subrank[-i] == 0:
                        win_recency = subDate[-i]
                win_indices = np.where(subrank == 0)[0]
                if len(win_indices) > 0:
                    win_frequency = len(win_indices) / date_interval
                else:
                    win_frequency = 0


            user=[tenure,participate_recency,participate_frequency,commit_recency,commit_frequency,
                  win_recency,win_frequency,last_perfromance]+skills.tolist()

            usernames.append(name)
            taskids.append(id)
            users.append(user)
            tasks.append(task)
            dates.append(date)
            curPerformance=self.subdata.getResultOfSubmit(name,id)
            if curPerformance is not None:
                submits.append(curPerformance[0])
                ranks.append(curPerformance[1])
            else:
                submits.append(0)
                ranks.append(10)

        print("missing task",missingtask,"missing user",missinguser,"instances size",len(taskids))
        print()
        data={}
        if len(usernames)==0:
            usernames=np.array([])
            taskids=np.array([])
            tasks=np.array([[]])
            users=np.array([[]])
            dates=np.array([])
            submits=np.array([[]])
            ranks=np.array([])

        data["usernames"] = usernames
        data["taskids"] = taskids
        data["tasks"] = tasks
        data["users"] = users
        data["dates"] = dates
        data["submits"] = submits
        data["ranks"] = ranks

        print("saving data")
        if self.localtasks is None:
            with open("../data/Instances/task_user"+str(choice)+".data","wb") as f:
                pickle.dump(data,f)

        return data

def genRegisteredInstances(gInst):

    '''
    x=np.array(user.memberage).reshape((len(user.memberage),1)).tolist()
    showData(x)
    showData(np.log(x).tolist())
    x = np.array(regs.regdate,dtype=np.int).reshape((len(regs.regdate), 1)).tolist()
    showData(x)
    showData(np.log(x).tolist())
    x = np.array(subs.subdate,dtype=np.int).reshape((len(subs.subdate), 1)).tolist()
    showData(x)
    showData(np.log(x).tolist())
    x = np.array(subs.score, dtype=np.int).reshape((len(subs.score), 1)).tolist()
    showData(x)
    showData(np.log(x).tolist())
    '''

    choice = 1
    local = False
    print("choice=", choice, "; local clusters=", local)

    if local:

        with open("../data/clusterResult/clusters" + str(choice) + ".data", "rb") as f:
            clusterdata = pickle.load(f)
            taskClusters=clusterdata["tasks"]
            taskidClusters=clusterdata["taskids"]
        dataClusters = {}
        print("creating train Local data")
        for k in taskClusters.keys():
            print("creating instances for cluster(%d):" % (len(taskidClusters[k])), k)
            gInst.setLocality(taskidClusters[k])
            data = gInst.createRegisteredInstances(choice)
            dataClusters[k] = data
            X = np.concatenate((data["tasks"], data["users"]), axis=1)
            print("instances size=", len(X))
            print()

        with open("../data/Instances/task_user_local" + str(choice) + ".data", "wb") as f:
            pickle.dump(dataClusters, f)

    else:
        print("creating global data")
        gInst.setLocality(None)
        data = gInst.createRegisteredInstances(choice)
        X = np.concatenate((data["tasks"], data["users"]), axis=1)
        print("instances size=", len(X))
        print()

def genWholeUserSet(gInst):

    choice=1


    data = gInst.createRegInstances(choice)
    if len(data["tasks"])==0:
        print("instances size=0")
        return
    X = np.concatenate((data["tasks"], data["users"]), axis=1)
    print("instances size=", len(X))
    # [print(x) for x in X[:3]]
    print()
def genActiveUserHistory(usernames,regdata,subdata):
    userData = {}
    for username in usernames:
        regids, regdates = regdata.getUserHistory(username)
        if len(regids) == 0:
            continue
        subids, subnum, subdates, score, rank = subdata.getUserHistory(username)
        userData[username] = {"regtasks": [regids, regdates],
                              "subtasks": [subids, subnum, subdates, score, rank]}
        print(username, "sub histroy and reg histrory=", len(userData[username]["subtasks"][0]),
              len(userData[username]["regtasks"][0]))

    print("saving history of %d active users" % len(userData))
    with open("../data/Instances/UserHistory/activeUsers2500.data", "wb") as f:
        pickle.dump(userData, f)

if __name__ == '__main__':
    user = Users()
    user.skills, features = onehotFeatures(user.skills)
    print("encoding skills feature_num=", features)
    regs = Registration()
    subs = Submission()
    gInst = DataInstances(regs, subs, user)
    gInst.loadActiveUsers()
    #genActiveUserHistory(user.getUsers(),regs,subs)
    genRegisteredInstances(gInst)
    #genWholeUserSet(gInst)

