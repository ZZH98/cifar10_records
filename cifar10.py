import torch
import torch.nn as tnn
import torchvision.datasets as dsets
import torchvision.transforms as transforms
from torch.autograd import Variable

import torch.nn.functional as F
import sys
import os
import json
from collections import OrderedDict

# device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
os.environ['CUDA_VISIBLE_DEVICES'] = '2'

batch_size = 32
learning_rate = 0.01
epoches = 40
n_classes = 10

dict = OrderedDict()

dict['epoches'] = epoches
dict['batch_size'] = batch_size
dict['learning_rate'] = learning_rate
dict['acc_record'] = []
dict['loss_record'] = []

save_path = "./model/model.pth"

data_transform = transforms.Compose([
    transforms.RandomResizedCrop(32),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize(mean = [ 0.485, 0.456, 0.406 ],
                         std  = [ 0.229, 0.224, 0.225 ]),
    ])

# cifar dataset
train_dataset = dsets.CIFAR10(root='./data', train=True, transform=data_transform, download=True)
test_dataset = dsets.CIFAR10(root='./data', train=False, transform=data_transform, download=True)

# Data loader
trainLoader = torch.utils.data.DataLoader(dataset=train_dataset, batch_size=batch_size, shuffle=True)
testLoader = torch.utils.data.DataLoader(dataset=test_dataset, batch_size=batch_size, shuffle=False)

class VGG16(tnn.Module):
    def __init__(self):
        super(VGG16, self).__init__()
        self.layer1 = tnn.Sequential(

            # 1-1 conv layer
            tnn.Conv2d(3, 64, kernel_size=3, padding=1),
            tnn.BatchNorm2d(64),
            tnn.ReLU(),

            # 1-2 conv layer
            tnn.Conv2d(64, 64, kernel_size=3, padding=1),
            tnn.BatchNorm2d(64),
            tnn.ReLU(),

            # 1 Pooling layer
            tnn.MaxPool2d(kernel_size=2, stride=2))

        self.layer2 = tnn.Sequential(

            # 2-1 conv layer
            tnn.Conv2d(64, 128, kernel_size=3, padding=1),
            tnn.BatchNorm2d(128),
            tnn.ReLU(),

            # 2-2 conv layer
            tnn.Conv2d(128, 128, kernel_size=3, padding=1),
            tnn.BatchNorm2d(128),
            tnn.ReLU(),

            # 2 Pooling lyaer
            tnn.MaxPool2d(kernel_size=2, stride=2))

        self.layer3 = tnn.Sequential(

            # 3-1 conv layer
            tnn.Conv2d(128, 256, kernel_size=3, padding=1),
            tnn.BatchNorm2d(256),
            tnn.ReLU(),

            # 3-2 conv layer
            tnn.Conv2d(256, 256, kernel_size=3, padding=1),
            tnn.BatchNorm2d(256),
            tnn.ReLU(),

            tnn.Conv2d(256, 256, kernel_size=3, padding=1),
            tnn.BatchNorm2d(256),
            tnn.ReLU(),

            # 3 Pooling layer
            tnn.MaxPool2d(kernel_size=2, stride=2))

        self.layer4 = tnn.Sequential(

            # 4-1 conv layer
            tnn.Conv2d(256, 512, kernel_size=3, padding=1),
            tnn.BatchNorm2d(512),
            tnn.ReLU(),

            # 4-2 conv layer
            tnn.Conv2d(512, 512, kernel_size=3, padding=1),
            tnn.BatchNorm2d(512),
            tnn.ReLU(),

            tnn.Conv2d(512, 512, kernel_size=3, padding=1),
            tnn.BatchNorm2d(512),
            tnn.ReLU(),

            # 4 Pooling layer
            tnn.MaxPool2d(kernel_size=2, stride=2))

        self.layer5 = tnn.Sequential(

            # 5-1 conv layer
            tnn.Conv2d(512, 512, kernel_size=3, padding=1),
            tnn.BatchNorm2d(512),
            tnn.ReLU(),

            # 5-2 conv layer
            tnn.Conv2d(512, 512, kernel_size=3, padding=1),
            tnn.BatchNorm2d(512),
            tnn.ReLU(),

            tnn.Conv2d(512, 512, kernel_size=3, padding=1),
            tnn.BatchNorm2d(512),
            tnn.ReLU(),

            # 5 Pooling layer
            tnn.MaxPool2d(kernel_size=2, stride=2))

        self.layer6 = tnn.Sequential(

            # 6 Fully connected layer
            # Dropout layer omitted since batch normalization is used.
            tnn.Linear(512*1*1, 4096),
            tnn.BatchNorm1d(4096),
            tnn.ReLU())


        self.layer7 = tnn.Sequential(

            # 7 Fully connected layer
            # Dropout layer omitted since batch normalization is used.
            tnn.Linear(4096, 4096),
            tnn.BatchNorm1d(4096),
            tnn.ReLU())

        self.layer8 = tnn.Sequential(

            # 8 output layer
            tnn.Linear(4096, n_classes),
            tnn.BatchNorm1d(n_classes),
            tnn.Softmax())

    def forward(self, x):
        out = self.layer1(x)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = self.layer5(out)
        vgg16_features = out.view(out.size(0), -1)
        out = self.layer6(vgg16_features)
        out = self.layer7(out)
        out = self.layer8(out)

        return vgg16_features, out


model = VGG16()
model = model.cuda()
model = torch.nn.DataParallel(model)

# Loss and Optimizer
loss_func = tnn.CrossEntropyLoss(size_average = False)
optimizer = torch.optim.Adam(model.parameters(), lr = learning_rate)

# Train the model
for epoch in range(epoches):
    print('epoch: ', epoch + 1)
    model.train()
    for i, (images, labels) in enumerate(trainLoader):
        images = images.cuda()
        labels = labels.cuda()

        # Forward + Backward + Optimize
        optimizer.zero_grad()
        _, outputs = model(images)
        loss = loss_func(outputs, labels)
        # outputs = F.log_softmax(outputs, dim = 1)
        # loss = F.nll_loss(outputs, labels)
        loss.backward()
        optimizer.step()

        if (i) % 100 == 0 :
            print ('batch_idx = %d, train_loss =  %.4f' %(i, loss.item()))

    # Test the model
    model.eval()
    correct = 0
    total_loss = 0

    for images, labels in testLoader:
        images = images.cuda()
        labels = labels.cuda()
        _, outputs = model(images)
        loss = loss_func(outputs, labels)
        total_loss += loss
        loss.backward()
        _, predicted = torch.max(outputs.data, 1)
        correct += (predicted == labels).sum()

    acc = float(correct) / len(testLoader.dataset)
    total_loss /= len(testLoader.dataset)
    print("%d/%d, acc = %f, test_loss = %f"%(correct, len(testLoader.dataset), acc, total_loss.item()))
    dict['acc_record'].append(acc)
    dict['loss_record'].append(total_loss.item())
    if (epoch == epoches - 1):
        dict['acc'] = acc
        dict['loss'] = total_loss.item()

# Save the Trained Model
torch.save(model.state_dict(), save_path)
with open("./record.json","w") as f:
    json.dump(dict, f, indent = 4)
