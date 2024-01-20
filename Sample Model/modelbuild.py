import tensorflow as tf
from tensorflow import keras
import os
# Chay bang CPU thay vi GPU
# os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
# Chay tiet kiem ram GPU
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
class buildmodel():
    def residual_block(self, inputs, filter,block_num,reduce=False):
        res = inputs
        x = keras.layers.Conv2D(filter,(3, 3), strides = 2 if reduce else 1,activation = 'relu', padding = 'same',name = f'conv_{block_num}_1')(res)
        x = keras.layers.Conv2D(filter,(3, 3), activation = 'relu', padding = 'same',name = f'conv_{block_num}_2')(x)
        if reduce == True:
            res = keras.layers.Conv2D(filter,(1, 1), strides = 2, activation = 'relu', padding = 'same',name = f'conv_skip_{block_num-1}')(res)
        res = keras.layers.Add(name = f'end_res_bock_{2*block_num-1}')([x,res])
        x = keras.layers.Conv2D(filter,(3, 3), activation = 'relu', padding = 'same',name = f'conv_{block_num}_3')(res)
        x = keras.layers.Conv2D(filter,(3, 3), activation = 'relu', padding = 'same',name = f'conv_{block_num}_4')(x)
        res = keras.layers.Add(name = f'end_res_bock_{2*block_num}')([x,res])
        return res
    
    def resnet18(self, num_outputs=1):
        # Inputs
        inputs = keras.layers.Input(shape=(224,224,3),name = 'input')
        x = keras.layers.Conv2D(64,(7, 7),strides = 2, activation = 'relu', padding = 'same',name = 'conv2D')(inputs)
        x = keras.layers.MaxPooling2D(pool_size = (3,3),strides = 2 ,padding = 'same',name = 'max_pool_1')(x)
        # Block 1
        x = self.residual_block(x,64,1,False)
        # Block 2
        x = self.residual_block(x,128,2,True)
        # Block 3
        x = self.residual_block(x,256,3,True)
        # Block 4
        x = self.residual_block(x,512,4,True)
        # Ouputs
        x = keras.layers.GlobalAveragePooling2D(name = 'global_pooling')(x)
        if num_outputs==1:
            outputs = keras.layers.Dense(num_outputs,activation = 'sigmoid',name = 'outputs_sigmoid')(x)
        else:
            outputs = keras.layers.Dense(num_outputs,activation = 'softmax',name = 'outputs_softmax')(x)
        model = keras.Model(inputs = inputs, outputs = outputs, name = 'resnet18')
        return model
    def __init__(self, optimizer=keras.optimizers.Adam(), loss=keras.losses.BinaryCrossentropy() , metrics=keras.metrics.BinaryAccuracy()):
        self.model = self.resnet18()
        self.optimizer = optimizer
        self.loss = loss
        self.metrics = metrics
        self.model.compile(optimizer = self.optimizer, loss = self.loss, metrics = self.metrics)
    def compile(self, optimizer=keras.optimizers.Adam(), loss=keras.losses.BinaryCrossentropy() , metrics=keras.metrics.BinaryAccuracy()):
        self.optimizer = optimizer
        self.loss = loss
        self.metrics = metrics
        self.model.compile(optimizer = self.optimizer, loss = self.loss, metrics = self.metrics)
    @tf.function
    def train_step(self,x,y):
        #Can chuyen y ve ma tran hai chieu neu huan luyen voi batch
        with tf.GradientTape() as tape:
            logits = self.model(x, training=True)
            loss_value = self.loss(y, logits)
        grads = tape.gradient(loss_value, self.model.trainable_weights)
        self.metrics.update_state(y, logits)
        return loss_value,grads
    @tf.function
    def optimize_model(self, grads):
        self.optimizer.apply_gradients(zip(grads, self.model.trainable_weights))