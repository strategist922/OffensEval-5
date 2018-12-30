import os
import gc
import torch
import argparse
import numpy as np
import torch.nn.functional as F
from torch.autograd import Variable
import torch.backends.cudnn as cudnn
from torch.utils.data import DataLoader

from models import *
from dataset import *
from utils import progress_bar


parser = argparse.ArgumentParser(description='PyTorch OffenseEval - run dataset.py first for word embeddings')
parser.add_argument('--lr', default=0.001, type=float, help='learning rate') # NOTE :  change for diff models
parser.add_argument('--batch_size', default=25, type=int)
parser.add_argument('--resume', '-r', type=int, default=0, help='resume from checkpoint')
parser.add_argument('--epochs', '-e', type=int, default=10, help='Number of epochs to train.')
parser.add_argument('--subtask', default='A', help="Sub-task for OffensEval")
parser.add_argument('--embedding_length', default=50, type=int)

args = parser.parse_args()

device = 'cuda' if torch.cuda.is_available() else 'cpu'
best_acc, tsepoch, tstep, lsepoch, lstep = 0, 0, 0, 0, 0

criterion = torch.nn.CrossEntropyLoss()

print('==> Preparing data..')

def collate_fn(data):
    data = list(filter(lambda x: type(x[1]) != int, data))
    audios, captions = zip(*data)
    data = None
    del data
    audios = torch.stack(audios, 0)
    return audios, captions


classes = {"A" : 2, "B" : 2, "C" : 3}
print('==> Creating network..')
net = LSTMClassifier(args.batch_size, classes[args.subtask], 25, args.embedding_length)
net = net.to(device)

if(args.resume):
    if(os.path.isfile('../save/network.ckpt')):
        net.load_state_dict(torch.load('../save/network.ckpt'))
        print('==> Network : loaded')

    if(os.path.isfile("../save/info.txt")):
        with open("../save/info.txt", "r") as f:
            tsepoch, tstep = (int(i) for i in str(f.read()).split(" "))
        print("=> Network : prev epoch found")
else :
    with open("../save/logs/train_loss.log", "w+") as f:
        pass 


def train_network(epoch):
    global tstep
    print('\n=> Epoch: {}'.format(epoch))
    net.train()
    
    dataset = OffenseEval(path='/home/nevronas/Projects/Personal-Projects/Dhruv/OffensEval/dataset/train-v1/offenseval-training-v1.tsv')
    dataloader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)#,  collate_fn=collate_fn)
    dataloader = iter(dataloader)

    train_loss = 0
    params = net.parameters()     
    optimizer = torch.optim.Adam(params, lr=args.lr) 

    for i in range(tstep, len(dataloader)):
        contents = next(dataloader)
        inputs, targets = torch.Tensor(contents["embeddings"]).to(device), torch.Tensor(contents[args.subtask]).to(device)

        optimizer.zero_grad()
        y_pred = net(inputs)
        loss = criterion(y_pred, targets)
        train_loss = loss.item()
        loss.backward()
        optimizer.step()

        gc.collect()
        torch.cuda.empty_cache()

        torch.save(net.state_dict(), '../save/network.ckpt')
        with open("../save/transform/info.txt", "w+") as f:
            f.write("{} {}".format(epoch, i))

        with open("../save/transform/logs/train_loss.log", "a+") as lfile:
            lfile.write("{}\n".format(train_loss))

        progress_bar(i, len(dataloader), 'Loss: {}, Con Loss: {}, Sty Loss: {} '.format(train_loss, tr_con, tr_sty))

    tstep = 0
    del dataloader
    print('=> Network : Epoch [{}/{}], Loss:{:.4f}'.format(epoch + 1, args.epochs, train_loss))


def test():
    # TODO
    pass


for epoch in range(tsepoch, tsepoch + args.epochs):
    train_network(epoch)

#test()