import tensorflow as tf
from tensorflow import keras

class buildmodel():
  def conv_block(self,inputs , filters, block_num,conv_num=2):
    x = keras.layers.Conv2D(filters,3, activation = 'relu', padding = 'same',name = 'conv_%d_1'%block_num)(inputs)
    x = keras.layers.Conv2D(filters,3, activation = 'relu', padding = 'same',name = 'conv_%d_2'%block_num)(x)
    if conv_num==3:
      x = keras.layers.Conv2D(filters,3, activation = 'relu', padding = 'same',name = 'conv_%d_3'%block_num)(x)
    x = keras.layers.MaxPooling2D(name = 'max_pooling_%d'%block_num)(x)
    return x

  def vgg16(self,num_outputs=1000):
    inputs = keras.layers.Input(shape=(224,224,3),name = 'input')
    x = self.conv_block(inputs,64,1)
    x = self.conv_block(x,128,2)
    x = self.conv_block(x,256,3,3)
    x = self.conv_block(x,512,4,3)
    x = self.conv_block(x,512,5,3)
    x = keras.layers.Flatten()(x)
    x = keras.layers.Dense(4096,activation = 'relu',name = 'dense_1')(x)
    x = keras.layers.Dense(4096,activation = 'relu',name = 'dense_2')(x)
    outputs = keras.layers.Dense(num_outputs,activation = 'softmax',name = 'outputs')(x)
    model = keras.Model(inputs = inputs, outputs = outputs, name = 'vgg16')
    return model

  def residual_block(self,inputs, filter,block_num,reduce=False):
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

  def resnet18(self,num_outputs=1000):
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
  def compiled_model(self,model_name = 'resnet18',num_outputs=1):
    if model_name == 'resnet18':
      model = self.resnet18(num_outputs = num_outputs)
    if model_name == 'vgg16':
      model = self.vgg16(num_outputs=num_outputs)
    model.compile(optimizer=keras.optimizers.Adam(),loss=keras.losses.BinaryCrossentropy())
    return model