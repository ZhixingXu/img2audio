import matplotlib.pyplot as plt
import numpy as np
import pyaudio
import wave
import cv2

def PreEmphasised(x,alpha=0.95):
    x=x[1:]-alpha*x[0:-1]
    return x

#计算每帧对应的时间
def FrameTimeC(frameNum, frameLen, inc, fs):
    ll = np.array([i for i in range(frameNum)])
    # return ((ll - 1) * inc + frameLen / 2) / fs
    return (ll * inc + frameLen / 2) / fs

#分帧函数
def enframe(x, win, inc=None):
    nx = len(x)
    if isinstance(win, list) or isinstance(win, np.ndarray):
        nwin = len(win)
        nlen = nwin  # 帧长=窗长
    elif isinstance(win, int):
        nwin = 1
        nlen = win  # 设置为帧长
    if inc is None:
        inc = nlen
    nf = (nx - nlen + inc) // inc
    frameout = np.zeros((nf, nlen))
    indf = np.multiply(inc, np.array([i for i in range(nf)]))
    # start framing data
    for i in range(nf):
        frameout[i, :] = x[indf[i]:indf[i] + nlen]
    # use window function
    if isinstance(win, list) or isinstance(win, np.ndarray):
        frameout = np.multiply(frameout, np.array(win))
    return frameout

def comframe(x,inc):
    out=np.array([])
    overlap=x.shape[1]-inc
    for row in x:
        if out.size<inc:
            out=np.append(out,row)
        else:
            out[-overlap:]+=row[0:overlap]
            out=np.append(out,row[overlap:])
    return out


def audio_export(out,fn="output.wav",channels=1,samwid=2,framerate=16000):
    fp=wave.open(fn,'wb')
    if fp is None:
        return False
    arr=out.astype(np.short)
    # 配置声道数、量化位数和取样频率
    fp.setnchannels(channels)
    fp.setsampwidth(samwid)
    fp.setframerate(framerate)
    # 将wav_data转换为二进制数据写入文件
    fp.writeframes(arr.tobytes())
    fp.close()
    return True

def find_min_pow(num:int)->int:
    p=np.floor(np.log2(num))
    return int(2**p)

def get_phase(data:np.ndarray,N=2048,size=(2048,1000))->np.ndarray:
    # fp       = wave.Wave_read(fn)
    # data     = fp.readframes(fp.getnframes())
    # data     = np.frombuffer(data, dtype='short')
    data=enframe(data,2048,inc=512)
    data=data.T
    spec=np.fft.fft(data,axis=0)
    print('spec:',spec.shape,',input size:',size)
    r,c=spec.shape
    if r!=size[0]:
        print("error")
        return -1
    if c>size[1]:
        spec=np.angle(spec)
        return spec[:,0:size[1]]
    else:
        while spec.shape[1]<size[1]:
            spec=np.c_[spec,spec]
        spec=np.angle(spec)
        return spec[:,0:size[1]]
    return -1

def generate_audio(pic_data:np.ndarray,aud_data:np.ndarray):
    
    origin_width=pic_data.shape[0]
    origin_height=pic_data.shape[1]

    tar_h=find_min_pow(origin_height)+1
    ratio=origin_height/tar_h
    tar_w=int(origin_width/ratio)

    pic_data=cv2.resize(pic_data,dsize=(tar_w,tar_h),fx=1,fy=1,interpolation=cv2.INTER_LINEAR)
    print(pic_data.shape)
    pic_data=np.mean(pic_data,axis=2)
    pic_data=pic_data-128
    print("max:",np.max(pic_data))
    ratio=128/np.max(pic_data)
    pic_data=ratio*pic_data
    index=pic_data<0
    pic_data=1.1**np.abs(pic_data)/100
    # -----------------------------
    if np.max(pic_data)>0x4fff:
        ratio=np.max(pic_data)/0x4fff
        pic_data=pic_data/ratio
    # --------------------------------
    pic_data[index]=-pic_data[index]
    pic_data=pic_data*pic_data.shape[0]
    pic_data=pic_data[::-1,:]
    
    pic_data=np.r_[pic_data,pic_data[-2:0:-1,:]]
    # ---------------------------------------------------------------------
    # 添加相频响应
    if aud_data is not None:
        pha=get_phase(aud_data,pic_data.shape[0],(pic_data.shape[0],pic_data.shape[1]))
        pic_data=pic_data*np.exp(1j*pha)
    # ---------------------------------------------------------------------
    nd=np.fft.ifft(pic_data,axis=0)
    # ------------------------------------------
    # 加窗
    for i in range(nd.shape[1]):
        nd[:,i]=nd[:,i]*np.hanning(nd.shape[0])
    # ------------------------------------------
    audio=comframe(nd.T,inc=nd.shape[0]//4)
    return np.real(audio)

def audio_play(play_data:np.ndarray,nchannel=1,sample_wid=2,fs=16000):
    chunk = 1024  
    # print("sample_wid:{},nchannel:{},fs:{}".format(sample_wid,nchannel,fs))
    p = pyaudio.PyAudio()
    stream = p.open(format=p.get_format_from_width(sample_wid), channels=nchannel,
                    rate=fs, output=True)

    less=play_data.size%chunk
    if less:
        print("less: ",less)
        less=chunk-less
        play_data=np.append(play_data,np.zeros(less))
    
    play_data=play_data.reshape(-1,chunk)
    play_data=play_data.astype('short')
    for row in play_data:
        stream.write(row.tobytes())
    stream.stop_stream()  # 停止数据流
    stream.close()
    p.terminate()  # 关闭 PyAudio