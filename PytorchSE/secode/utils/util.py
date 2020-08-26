import librosa,os
import numpy as np
from pypesq import pesq
from pystoi.stoi import stoi
import scipy
import tqdm

epsilon = np.finfo(float).eps

def getfilename(folder):

    fnlist=[]
    for dirpath, _, files in os.walk(folder):
        for file_name in files:
            if file_name.endswith(".wav") or file_name.endswith(".WAV") or file_name.endswith(".pt"):
                fnlist.append(os.path.join(dirpath, file_name))
                
    
    print('folder:',folder,', len:',len(fnlist))
    return fnlist

def get_cleanwav_dic(clean_wav_path):
    print('get clean wav path:', clean_wav_path)
    clean_wav=getfilename(clean_wav_path)
    c_files = np.array(clean_wav)
    c_dict={}
    for c_ in c_files:
        c_tmp=c_.replace('.WAV','').split('/')
        k=c_tmp[-2]+'_'+c_tmp[-1]
        c_path=c_.replace(c_tmp[-2]+'/'+c_tmp[-1]+'.WAV','')
        c_dict[k]=c_path
    return c_dict



def check_path(path):
    if not os.path.isdir(path): 
        os.makedirs(path)
        
def check_folder(path):
    path_n = '/'.join(path.split('/')[:-1])
    check_path(path_n)

def cal_score(clean,enhanced):
    clean = clean/abs(clean).max()
    enhanced = enhanced/abs(enhanced).max()

    s_stoi = stoi(clean, enhanced, 16000)
    s_pesq = pesq(clean, enhanced, 16000)
    
    return round(s_pesq,5), round(s_stoi,5)


#def get_filepaths(directory,folders='BabyCry.wav,cafeteria_babble.wav',ftype='.wav'):
#    file_paths = []
#    folders = folders.split(',')
#    with open(directory, 'r') as f:
#        for line in f:
#            if str(line.split('/')[-3]) in folders:
#                file_paths.append(line[:-1])
#    return file_paths



    '''
    for root, directories, files in os.walk(directory):
        for filename in files:
            if filename.endswith(ftype):
                filepath = os.path.join(root, filename)
                file_paths.append(filepath)  # Add it to the list.
    return sorted(file_paths)
    '''


def make_spectrum(filename=None, y=None, is_slice=False, feature_type='logmag', mode=None, FRAMELENGTH=400, SHIFT=160, _max=None, _min=None):
    if y is not None:
        y = y
    else:
        y, sr = librosa.load(filename, sr=16000)
        if sr != 16000:
            raise ValueError('Sampling rate is expected to be 16kHz!')
        if y.dtype == 'int16':
            y = np.float32(y/32767.)
        elif y.dtype !='float32':
            y = np.float32(y)

    ### Normalize waveform
    # y = y / np.max(abs(y)) / 2.
    
    D = librosa.stft(y,center=False, n_fft=FRAMELENGTH, hop_length=SHIFT,win_length=FRAMELENGTH,window=scipy.signal.hamming)
    utt_len = D.shape[-1]
    phase = np.exp(1j * np.angle(D))
    D = np.abs(D)

    ### Feature type
    if feature_type == 'logmag':
        Sxx = np.log1p(D)
    elif feature_type == 'lps':
        Sxx = np.log10(D**2)
    else:
        Sxx = D

    if mode == 'mean_std':
        mean = np.mean(Sxx, axis=1).reshape(((hp.n_fft//2)+1, 1))
        std = np.std(Sxx, axis=1).reshape(((hp.n_fft//2)+1, 1))+1e-12
        Sxx = (Sxx-mean)/std  
    elif mode == 'minmax':
        Sxx = 2 * (Sxx - _min)/(_max - _min) - 1

    return Sxx, phase, len(y)

def recons_spec_phase(Sxx_r, phase, length_wav, feature_type='logmag'):
    if feature_type == 'logmag':
        Sxx_r = np.expm1(Sxx_r)
        if np.min(Sxx_r) < 0:
            print("Expm1 < 0 !!")
        Sxx_r = np.clip(Sxx_r, a_min=0., a_max=None)
    elif feature_type == 'lps':
        Sxx_r = np.sqrt(10**Sxx_r)

    R = np.multiply(Sxx_r , phase)
    result = librosa.istft(R,
                     center=False,
                     hop_length=160,
                     win_length=400,
                     window=scipy.signal.hamming,
                     length=length_wav)
    return result
