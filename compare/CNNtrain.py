import numpy as np
import pandas as pd
import lightgbm as lgb
from hyperopt import fmin, tpe, hp, partial, Trials, STATUS_OK,STATUS_FAIL
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, zero_one_loss,mean_absolute_error,r2_score
import matplotlib.pyplot as plt
import time
from math import sqrt
import os
from tensorflow import keras
from keras_layer_normalization import LayerNormalization
# from loss import LossHistory
import math
import tensorflow.compat.v1 as tf
config = tf.ConfigProto()
config.gpu_options.allow_growth=True
sess = tf.Session(config=config)
print(tf.__version__)

def dataProvider(train1, train2, windowsize):
    offset = int(0.5 * (windowsize - 1.0))
    data_frame1 = pd.read_csv(train1,
                             #chunksize=10 ** 3,
                             header=0
                             )
    data_frame2 = pd.read_csv(train2,
                             #chunksize=10 ** 3,
                             header=0
                             )

    np_array = np.array(data_frame1)
    inputs, targets = np_array[:, 0], np_array[:, 1]
    window_num=inputs.size - 2 * offset
    features=list()
    labels=list()
    for i in range(0,window_num):
        inp=inputs[i:i+windowsize]
        tar=targets[i+offset]
        features.append(inp)
        labels.append(tar)
    features0=np.array(features)
    labels0=np.array(labels)

    np_array = np.array(data_frame2)
    inputs, targets = np_array[:, 0], np_array[:, 1]
    window_num=inputs.size - 2 * offset
    features=list()
    labels=list()
    for i in range(0,window_num):
        inp=inputs[i:i+windowsize]
        tar=targets[i+offset]
        features.append(inp)
        labels.append(tar)
    features1=np.array(features)
    labels1=np.array(labels)
    feature=np.concatenate((features0, features1), axis=0)
    label=np.concatenate((labels0, labels1), axis=0)
    return feature, label



space = {"layer1_output": hp.randint("layer1_output", 200),
         "layer2_output": hp.randint("layer2_output", 200),
         "layer1_dropout": hp.uniform("layer1_dropout", 0, 1),
         "layer2_dropout": hp.uniform("layer2_dropout", 0, 1),
         "layer1_rdropout": hp.uniform('layer1_rdropout', 0, 1),
         "layer2_rdropout": hp.uniform('layer2_rdropout', 0, 1),
         "layer3_dropout": hp.uniform('layer3_dropout', 0, 1),
         #"optimizer": hp.choice('optimizer', ['adam', 'sgd']),
         "momentum": hp.uniform('momentum', 0,1),
         "lr": hp.uniform('lr', 1e-9, 1e-3),
         "decay": hp.uniform('decay', 1e-9, 1e-3),
         'epochs': hp.randint('epochs', 250),
         'batch_size': hp.randint('batch_size', 100),
         'time_step':hp.randint('time_step',13)
         }

def argsDict_tranform(argsDict):
    argsDict["layer1_output"] = argsDict["layer1_output"] + 20
    argsDict['layer2_output'] = argsDict['layer2_output'] + 20
    argsDict['epochs'] = argsDict['epochs'] + 50
    argsDict['batch_size'] = argsDict['batch_size'] + 32
    argsDict['time_step']=argsDict['time_step']+1
    return argsDict

windowsize=19



def CNN_training(argsDic):
    argsDic=argsDict_tranform(argsDic)
    model=keras.models.Sequential()
    # model.add(LayerNormalization())
    model.add(keras.layers.Reshape((-1,windowsize, 1), input_shape=(19,)))
    model.add(keras.layers.BatchNormalization())
    model.add(keras.layers.Conv2D(filters=30,
                  kernel_size=(10, 1),
                  strides=(1, 1),
                  padding='same',
                  activation='relu',
                  ))
    model.add(keras.layers.Conv2D(filters=30,
                  kernel_size=(8, 1),
                  strides=(1, 1),
                  padding='same',
                  activation='relu',
                  ))
    model.add(keras.layers.Conv2D(filters=40,
                  kernel_size=(6, 1),
                  strides=(1, 1),
                  padding='same',
                  activation='relu',
                  ))
    model.add(keras.layers.Conv2D(filters=50,
                  kernel_size=(5, 1),
                  strides=(1, 1),
                  padding='same',
                  activation='relu',
                  ))
    model.add(keras.layers.Conv2D(filters=50,
                  kernel_size=(5, 1),
                  strides=(1, 1),
                  padding='same',
                  activation='relu',
                  ))
    model.add(LayerNormalization())
    model.add(keras.layers.Flatten(name='flatten'))
    model.add(keras.layers.BatchNormalization())
    model.add(keras.layers.Dense(1024, activation='relu', name='dense'))
    model.add(keras.layers.BatchNormalization())
    model.add(keras.layers.Dense(1, activation='linear', name='output'))
    adam = keras.optimizers.Adam(learning_rate=argsDict["lr"],
                                  beta_1=0.9,
                                  beta_2=0.999,
                                  epsilon=1e-08)
                                  # use_locking=False)
    model.compile(optimizer=adam, loss='mean_squared_error', metrics=['mae'])
    print('start training')
    model.fit(x_train_all,y_train_all, epochs=argsDict['epochs'], batch_size=argsDict['batch_size'], validation_split=0.2)
    loss=get_tranformer_score(model, x_predict, y_predict)
    if(loss==10):
        return {'loss':loss, 'status':STATUS_FAIL}

    else:
        return {'loss':loss, 'status':STATUS_OK}

def get_tranformer_score(tranformer,x_predict, y_predict):
    gru = tranformer
    prediction = gru.predict(x_predict)
    # for i in prediction:
    #     if math.isnan(i[0]):
    #         print('nan number is found')
    #         return 10
    r = y_predict.sum()
    r0 = prediction.sum()
    sae=abs(r0 - r) / r
    #print("the new model sae is :", abs(r0 - r) / r)
    return mean_absolute_error(y_predict, prediction), sae

def CNN_training_best(argsDict,name):
    x_train_all, x_predict, y_train_all, y_predict = train_test_split(X, Y, test_size=0.2, random_state=100)
    del X, Y
    argsDic=argsDict_tranform(argsDic)
    model=keras.models.Sequential()
    # model.add(LayerNormalization())
    model.add(keras.layers.Reshape((-1, windowsize, 1),input_shape=(19,)))
    model.add(keras.layers.BatchNormalization())
    model.add(keras.layers.Conv2D(filters=30,
                  kernel_size=(10, 1),
                  strides=(1, 1),
                  padding='same',
                  activation='relu',
                  ))
    model.add(keras.layers.Conv2D(filters=30,
                  kernel_size=(8, 1),
                  strides=(1, 1),
                  padding='same',
                  activation='relu',
                  ))
    model.add(keras.layers.Conv2D(filters=40,
                  kernel_size=(6, 1),
                  strides=(1, 1),
                  padding='same',
                  activation='relu',
                  ))
    model.add(keras.layers.Conv2D(filters=50,
                  kernel_size=(5, 1),
                  strides=(1, 1),
                  padding='same',
                  activation='relu',
                  ))
    model.add(keras.layers.Conv2D(filters=50,
                  kernel_size=(5, 1),
                  strides=(1, 1),
                  padding='same',
                  activation='relu',
                  ))
    model.add(LayerNormalization())
    model.add(keras.layers.Flatten(name='flatten'))
    model.add(keras.layers.BatchNormalization())
    model.add(keras.layers.Dense(1024, activation='relu', name='dense'))
    model.add(keras.layers.BatchNormalization())
    model.add(keras.layers.Dense(1, activation='linear', name='output'))
    adam = keras.optimizers.Adam(learning_rate=argsDict["lr"],
                                  beta_1=0.9,
                                  beta_2=0.999,
                                  epsilon=1e-08)
                                  # use_locking=False)
    model.compile(optimizer=adam, loss='mean_squared_error', metrics=['mae'])
    print('start training')
    model.fit(x_train_all,y_train_all, epochs=argsDict['epochs'], batch_size=argsDict['batch_size'], validation_split=0.2)
    loss,sae=get_tranformer_score(model, x_predict, y_predict)
    model.save('/NILM/CNN/UKDALE/'+str(name)+'.h5')
    time_start=time.time()
    result=model.predict(x_predict)
    time_end=time.time()
    result = result * ((Y.max(axis=0) - Y.min(axis=0))) + Y.min(axis=0)
    y_real = y_predict * ((Y.max(axis=0) - Y.min(axis=0))) + Y.min(axis=0)
    print('totally cost', time_end - time_start)
    print("rmse is ：", sqrt(mean_squared_error(y_real, result)))
    print("mae is ：", mean_absolute_error(y_real, result))
    print('r2 is :', r2_score(y_real, result))
    return model

def get_sae(target, prediction):
    # assert (target.shape == prediction.shape)

    r = target.sum()
    r0 = prediction.sum()
    sae = abs(r0 - r) / r
    print("targe sum is :", r)
    print("prediction sum is:", r0)
    return sae

trainfile1="F:/NILM/ukdale_training/fridge_house_2_training_.csv"
trainfile2="F:/NILM/ukdale_training/microwave_house_2_training_.csv"

X, Y = dataProvider(trainfile1, trainfile2, windowsize=19)
x_train_all, x_predict, y_train_all, y_predict = train_test_split(X, Y, test_size=0.2, random_state=100)
del X,Y
x_train, x_test, y_train, y_test = train_test_split(x_train_all, y_train_all, test_size=0.2, random_state=100)


time_start=time.time()
trials = Trials()
algo = partial(tpe.suggest, n_startup_jobs=20)
best = fmin(CNN_training, space, algo=algo, max_evals=200, pass_expr_memo_ctrl=None, trials=trials)
name='fridge'
bestModel= CNN_training_best(best,name)
time_end=time.time()










