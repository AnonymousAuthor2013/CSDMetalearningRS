from DataPrepare.ConnectDB import *
from gensim import corpora
import gensim
from nltk.corpus import stopwords
from nltk.stem.wordnet import WordNetLemmatizer
import string
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import Normalizer
from sklearn import metrics,preprocessing
from sklearn.cluster import KMeans, MiniBatchKMeans
import numpy as np
import matplotlib.pyplot as plt
import time
from scipy import sparse
import json
import pickle
import gc
gc.collect()
##############################################################################

class Vectorizer:
    def loadData(self):
        conn = ConnectDB()
        cur = conn.cursor()
        sqlcmd = 'select taskid,detail,taskname, duration,technology,languages,prize,postingdate,diffdeg,tasktype from task'
        cur.execute(sqlcmd)
        dataset = cur.fetchall()
        self.ids=[]
        self.docs=[]
        self.duration=[]
        self.prize=[]
        self.techs=[]
        self.lan=[]
        self.startdate=[]
        self.diffdeg=[]
        self.tasktype=[]
        for data in dataset:
            print(data)
            self.ids.append(data[0])

            if data[1] is None:
                self.docs.append(data[2])
            else:
                self.docs.append(data[2]+"\n"+data[1])

            self.duration.append([data[3]])
            self.techs.append(data[4])
            self.lan.append(data[5])
            if data[6]!='':
                self.prize.append([np.sum(eval(data[6]))])
            else:
                self.prize.append([0.])

            self.startdate.append([data[7]])
            self.diffdeg.append([data[8]])
            self.tasktype.append(data[9])

        print("docs num=%d" % len(self.ids))
    def countFeatures(self,data):
        c=set()
        for r in data:
            if r is None:
                r=''
            xs=r.split(",")
            for x in xs:
                c.add(x)

        i_c={}
        count=0
        for i in c:
            i_c[i]=count
            count+=1
        X = sparse.dok_matrix((len(data), count))
        row=0
        for r in data:
            if r is None:
                r=''
            xs=r.split(",")
            for x in xs:
                col=i_c[x]
                X[row,col]=1
            row+=1
        return X.toarray()
class LDAFlow(Vectorizer):
    def __init__(self):
        self.n_features=200

    def cleanDocs(self,docs):
        stop = set(stopwords.words('english'))
        exclude = set(string.punctuation)
        lemma = WordNetLemmatizer()
        for i in range(len(docs)):
            doc = docs[i]
            doc = " ".join([i for i in doc.lower().split() if i not in stop])
            doc = ''.join(ch for ch in doc if ch not in exclude)
            doc = " ".join(lemma.lemmatize(word) for word in doc.split())
            docs[i] = doc.split()
        return docs

    def transformVec(self,docs):
        #print(np.shape(docs),docs[0])
        docs=self.cleanDocs(docs)

        X = sparse.dok_matrix((len(docs), self.n_features))
        row = 0
        for doc in docs:
            doc_bow = self.dictionary.doc2bow(doc)
            lda_doc = self.lda[doc_bow]
            # print(type(lda_doc),lda_doc)
            for topic in lda_doc:
                X[row, topic[0]] = topic[1]
            row += 1
        return X

    def train_doctopics(self,docs):
        #print(np.shape(docs),docs[0])
        t0 = time.time()
        print("performing LDA ")
        docs = self.cleanDocs(docs)
        print("docs cleaning finished")
        self.dictionary = corpora.Dictionary(docs)
        doc_term_matrix = [self.dictionary.doc2bow(doc) for doc in docs]
        self.lda = gensim.models.LdaModel(doc_term_matrix, num_topics=self.n_features, id2word=self.dictionary)
        print("LDA built in %fs" % (time.time() - t0))

#######################################################################################################################
def hashingIDF(n_features):
    # Perform an IDF normalization on the output of HashingVectorizer
    hasher = HashingVectorizer(n_features=n_features,
                                stop_words='english', alternate_sign=False,
                                norm=None, binary=False)
    vectorizer = make_pipeline(hasher, TfidfTransformer())

    return vectorizer

def IDF(n_features):
    vectorizer = TfidfVectorizer(max_df=0.5, max_features=n_features,
                                 min_df=2, stop_words='english',
                                 use_idf=True)
    return vectorizer

class LSAFlow(Vectorizer):
    def __init__(self):
        self.n_features=200

    def transformVec(self,docs):
        X=IDF(self.n_features*10).fit_transform(docs)
        X = self.lsa.fit_transform(X)
        return X
    def train_doctopics(self,docs):
        t0 = time.time()

        X = IDF(self.n_features*10).fit_transform(docs)
        print("Performing  LSA")
        # Vectorizer results are normalized, which makes KMeans behave as
        # spherical k-means for better results. Since LSA/SVD results are
        # not normalized, we have to redo the normalization.
        svd = TruncatedSVD(self.n_features)
        normalizer = Normalizer(copy=False)
        self.lsa = make_pipeline(svd, normalizer)
        X = self.lsa.fit_transform(X)
        explained_variance = svd.explained_variance_ratio_.sum()
        print("Explained variance of the SVD step: {}%".format(
            int(explained_variance * 100)))

        print("LSA built in %fs" % (time.time() - t0))

#######################################################################################################################

# Do the actual clustering
n_clusters=20

def KM_cluster(X,true_k,minibatch=False):
    if minibatch:
        km = MiniBatchKMeans(n_clusters=true_k, init='k-means++', n_init=1,
                             init_size=1000, batch_size=1000, verbose=True)
    else:
        km = KMeans(n_clusters=true_k, init='k-means++', max_iter=100, n_init=1,
                    verbose=True)

    print("Clustering sparse data with %s" % km)
    km.fit(X)
    print()
    return km

#evalute cluster result in several metrics
def evaluateCluster(X,labels,km):
    print("Homogeneity: %0.3f" % metrics.homogeneity_score(labels, km.labels_))
    print("Completeness: %0.3f" % metrics.completeness_score(labels, km.labels_))
    print("V-measure: %0.3f" % metrics.v_measure_score(labels, km.labels_))
    print("Adjusted Rand-Index: %.3f"
          % metrics.adjusted_rand_score(labels, km.labels_))
    print("Silhouette Coefficient: %0.3f"
          % metrics.silhouette_score(X, km.labels_, sample_size=1000))

    print()

def scaler(X):
    minmax=preprocessing.MinMaxScaler(feature_range=(0,1))
    minmax.fit_transform(X)
    return minmax.transform(X)
def concatenateTasks(model,X):
    #weight of topics,techs,languages,postingdate,duration,prize,diffdeg,tasktype
    w=[1.0,2.0,1.5,1.0,1.0,3.0,3.0,6.0]
    X_techs=scaler(model.countFeatures(model.techs))
    X_lans=scaler(model.countFeatures(model.lan))
    X_startdate=scaler(model.startdate)
    X_duration=scaler(model.duration)
    X_prize=scaler(model.prize)
    X_diffdeg=scaler(model.diffdeg)
    X_tasktype=scaler(model.countFeatures(model.tasktype))

    X=np.concatenate((w[0]*X,w[1]*X_techs),axis=1)
    X=np.concatenate((X,w[2]*X_lans),axis=1)
    X=np.concatenate((X,w[3]*X_startdate),axis=1)
    X=np.concatenate((X,w[4]*X_duration),axis=1)
    X=np.concatenate((X,w[5]*X_prize),axis=1)
    X=np.concatenate((X,w[6]*X_diffdeg),axis=1)
    X=np.concatenate((X,w[7]*X_tasktype),axis=1)

    return X

def testResults():
    X=None
    model=None
    choice=eval(input("1:LDA; 2:LSA \t"))
    if choice==1:
        lda=LDAFlow()
        lda.loadData()
        lda.train_doctopics(lda.docs)
        lda.loadData()
        X=lda.transformVec(lda.docs)

        model=lda
    else:
        choice=2
        lsa=LSAFlow()
        lsa.loadData()
        lsa.train_doctopics(lsa.docs)
        X=lsa.transformVec(lsa.docs)

        model=lsa

    taskid=model.ids
    X = concatenateTasks(model, X)
    print("vec representation of tasks")
    with open("../data/taskVec"+str(choice)+".json","w") as f:
        data={}
        for i in range(len(taskid)):
            data[taskid[i]]=X[i]
        json.dump(data,f)

    n_clusters=30
    taskClusters=None
    while n_clusters>0:
        km=KM_cluster(X,n_clusters,minibatch=True)
        print("n_samples: %d, n_features: %d" % X.shape)
        print()

        result=km.predict(X)
        taskClusters={}
        for i in range(n_clusters):
            taskClusters[i]=[]
        for i in range(len(result)):
            c_no=result[i]
            taskClusters[c_no].append(taskid[i])

        #plot result
        hist=[(k,len(taskClusters[k])) for k in taskClusters.keys()]
        for i in hist:
            print(i)
        plt.plot(hist,marker='o')
        plt.show()
        n_clusters=eval(input("current cluster size is %d"%n_clusters))

    #saving result
    print("saving clustering result")
    with open("clusters" + str(choice) + ".json", "w") as f:
        json.dump(taskClusters, f, ensure_ascii=False)
        f.write("\n")
if __name__ == '__main__':
    testResults()
