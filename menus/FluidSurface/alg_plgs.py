from imagepy.core.engine import Filter, Simple
from imagepy.ipyalg import watershed
from imagepy import IPy
import os.path as osp
import numpy as np
import cv2

def combine(img):
    h,w = img.shape
    l, r = img[:,:w//2], img[:,w//2:]
    return np.hstack((l.T[::-1,:], r.T[:,::-1]))

class Combine(Simple):
    title = 'Re Combine'
    note = ['8-bit']
    
    #process
    def run(self, ips, imgs, para = None):
        for i in range(len(imgs)):
            imgs[i] = combine(imgs[i])
            self.progress(i, len(imgs))
        ips.set_imgs(imgs)

class Dark(Filter):
    title = 'Dark Little'
    note = ['all', 'auto_msk', 'auto_snap']

    def run(self, ips, snap, img, para = None):
        np.multiply(snap, 0.95, out=img, casting='unsafe')
        img += 1

class DOG(Filter):
    title = 'Fast DOG'
    note = ['all', 'auto_msk', 'auto_snap', 'preview']

    #parameter
    para = {'sigma':0}
    view = [(float, (0,30), 1,  'sigma', 'sigma', 'pix')]

    #process
    def run(self, ips, snap, img, para = None):
        l = int(para['sigma']*3)*2+1
        cv2.GaussianBlur(snap, (l, l), para['sigma'], dst=img)
        msk = img<snap
        img-=snap
        img[msk] = 0

class Watershed(Filter):
    title = 'Watershed Surface'
    note = ['8-bit', 'auto_snap', 'not_channel', 'preview']

    #process
    def run(self, ips, snap, img, para = None):
        markers = img*0
        markers[[0,-1]] = [[1],[2]]
        mark = watershed(img, markers, line=True, conn=1)
        img[:] = (mark==0) * 255

class Predict(Filter):
    model = None
    title = 'Predict Surface'
    note = ['8-bit', 'auto_snap',  'preview']
    mode_list=['msk','line','line on ori']
    view = [(list, mode_list, str, 'mode', 'mode', '')]
    para = {'mode':mode_list[0]}

    def load(self, ips):
        if not Predict.model is None: return True
        from keras.models import load_model
        try:
            path = osp.join(osp.abspath(osp.dirname(__file__)), 'U-net.h5')
            Predict.model=load_model(path)
        except Exception as e:
            IPy.alert('Not Found Net')
            return False
        #一定要预测一次，否则后面会出错        
        Predict.model.predict(np.zeros((1, 224,224,1)))     
        return True 

    def run(self, ips, snap, img, para = None):
        shape_temp=snap.shape
        temp=cv2.resize(snap,(224,224)).reshape(1,224,224,1).astype('float32')/255.0
        pred=(Predict.model.predict(temp)*255).astype('uint8').reshape(224,224)
        img[:]=(cv2.resize(pred,(shape_temp[1],shape_temp[0]))>127)*255
        
        if para['mode']=='msk':return
        line = cv2.dilate(img, np.array([[0,1,0],[1,1,1],[0,1,0]], dtype=np.uint8))
        if para['mode']=='line':img[:] = line -img
        if para['mode']=='line on ori': np.max([snap, line-img], axis=0, out=img)

plgs = [Combine, Dark, '-', DOG, Watershed, Predict]
