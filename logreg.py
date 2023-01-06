# -*- coding: utf-8 -*-
"""Untitled12.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1McM3_yWIDVGRhf7RRubZsBWzCDydHvwc
"""

import torch
from torchvision import transforms, datasets
import numpy as np
import timeit
from collections import OrderedDict
from pprint import pformat
import torch.nn as nn
from torch.utils.data.dataset import random_split

torch.multiprocessing.set_sharing_strategy('file_system')


class LogisticRegression(nn.Module):
    def __init__(self, input_dim):
        super(LogisticRegression, self).__init__()
        self.fc = nn.Linear(input_dim, 10)

    def forward(self, x):
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        return x


# Following code appears at:  https://lirnli.wordpress.com/2017/09/03/one-hot-encoding-in-pytorch/
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class One_Hot(nn.Module):
    def __init__(self, depth):
        super(One_Hot, self).__init__()
        self.depth = depth
        self.ones = torch.sparse.torch.eye(depth).to(device)

    def forward(self, X_in):
        X_in = X_in.long()
        return self.ones.index_select(0, X_in.data)

    def __repr__(self):
        return self.__class__.__name__ + "({})".format(self.depth)


def run(algorithm, dataset_name, filename):
    start = timeit.default_timer()
    predicted_test_labels, gt_labels = algorithm(dataset_name)
    if predicted_test_labels is None or gt_labels is None:
        return 0, 0, 0
    stop = timeit.default_timer()
    run_time = stop - start

    np.savetxt(filename, np.asarray(predicted_test_labels))

    correct = 0
    total = 0
    for label, prediction in zip(gt_labels, predicted_test_labels):
        total += label.size(0)
        correct += (prediction.cpu().numpy() == label.cpu().numpy()).sum().item()  # assuming your model runs on GPU

    accuracy = float(correct) / total

    print('Accuracy of the network on the 10000 test images: %d %%' % (100 * correct / total))
    return correct, accuracy, run_time



def logistic_regression(dataset_name):
    batch_size_train = 128
    batch_size_test = 1000
    input_dim = None
    training_set = None
    validation_set = None

    if dataset_name == "MNIST":
        training_dataset = datasets.MNIST('/MNIST_dataset/', train=True, download=True,
                                          transform=transforms.Compose([
                                              transforms.ToTensor(),
                                              transforms.Normalize((0.1307,), (0.3081,))]))
        test_dataset = datasets.MNIST('/MNIST_dataset/', train=False, download=True,
                                      transform=transforms.Compose([
                                          transforms.ToTensor(),
                                          transforms.Normalize((0.1307,), (0.3081,))]))

        input_dim = 28 * 28
        n_epochs = 10
        learning_rate = 0.001
        weight_lambda = 0.001

        training_set, validation_set = random_split(training_dataset, [48000, 12000])

        train_loader = torch.utils.data.DataLoader(training_set, batch_size_train, True)

        validation_loader = torch.utils.data.DataLoader(validation_set, batch_size_train, True)

        test_loader = torch.utils.data.DataLoader(test_dataset, batch_size_test, True)

        logistic_regression_model = LogisticRegression(input_dim).to(device)
        optimizer = torch.optim.Adam(logistic_regression_model.parameters(), lr=learning_rate,
                                     weight_decay=weight_lambda)



    else:
        training_dataset = datasets.CIFAR10(root="./data", train=True, download=True, transform=transforms.ToTensor())
        test_dataset = datasets.CIFAR10(root="./data", train=False, download=True, transform=transforms.ToTensor())

        input_dim = 3 * 32 * 32
        n_epochs = 23
        learning_rate = 0.0001
        weight_lambda = 0.001

        training_set, validation_set = random_split(training_dataset, [40000, 10000])
        train_loader = torch.utils.data.DataLoader(training_set, batch_size=batch_size_train, shuffle=True)

        validation_loader = torch.utils.data.DataLoader(validation_set, batch_size=batch_size_train, shuffle=True)

        test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=batch_size_test, shuffle=True)

        logistic_regression_model = LogisticRegression(input_dim).to(device)
        optimizer = torch.optim.Adam(logistic_regression_model.parameters(), lr=learning_rate,
                                     weight_decay=weight_lambda)
    one_hot = One_Hot(10).to(device)

    for epoch in range(n_epochs):
        train(logistic_regression_model, train_loader, one_hot, optimizer)
        validation(logistic_regression_model, validation_loader, one_hot)
    predicted_test_labels, gt_labels = test(logistic_regression_model, test_loader)

    return predicted_test_labels, gt_labels


def train(logistic_regression_model, train_loader, one_hot, optimizer):
    logistic_regression_model.train()
    for batch_idx, (data, target) in enumerate(train_loader):
        data = data.to(device)
        target = target.to(device)
        optimizer.zero_grad()
        output = logistic_regression_model(data)
        loss = torch.nn.functional.cross_entropy(output, one_hot(target))
        loss.backward()
        optimizer.step()


def validation(logistic_regression_model, validation_loader, one_hot):
    logistic_regression_model.eval()
    validation_loss = 0
    correct = 0
    with torch.no_grad():
        for data, target in validation_loader:
            data = data.to(device)
            target = target.to(device)
            output = logistic_regression_model(data)
            pred = output.data.max(1, keepdim=True)[1]
            correct += pred.eq(target.data.view_as(pred)).sum()
            validation_loss += torch.nn.functional.cross_entropy(output, one_hot(target), size_average=False).item()
    validation_loss /= len(validation_loader.dataset)
    print('\nValidation set: Avg. loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n'.format(validation_loss, correct,
                                                                                    len(validation_loader.dataset),
                                                                                    100. * correct / len(
                                                                                        validation_loader.dataset)))
    return 100. * correct / len(validation_loader.dataset)


def test(logistic_regression_model, test_loader):
    predicted_test_labels = []
    gt_labels = []
    logistic_regression_model.eval()
    with torch.no_grad():
        for data, target in test_loader:
            data = data.to(device)
            target = target.to(device)
            output = logistic_regression_model(data)
            pred = output.data.max(1, keepdim=True)[1]
            predicted_test_labels.append(pred.cpu())
            gt_labels.append(target.data.view_as(pred).cpu())

    predicted_test_labels = torch.cat(predicted_test_labels, axis=0)
    gt_labels = torch.cat(gt_labels, axis=0)

    return predicted_test_labels, gt_labels


def tune_hyper_parameter():
    learning_rates = [1e-2, 1e-3, 1e-4]
    lambda_values = [0.001, 0.01]
    n_epochs = 23
    batch_size_train = 128
    batch_size_test = 1000

    training_dataset = datasets.CIFAR10(root="./data", train=True, download=True, transform=transforms.ToTensor())

    training_set, validation_set = random_split(training_dataset, [40000, 10000])

    train_loader = torch.utils.data.DataLoader(training_set, batch_size=batch_size_train, shuffle=True)

    validation_loader = torch.utils.data.DataLoader(validation_set, batch_size=batch_size_train, shuffle=True)

    input_dim = 3 * 32 * 32

    start = timeit.default_timer()
    best_acc = 0.0
    best_params = []
    for learning_rate in learning_rates:
        for lv in lambda_values:
            logistic_regression_model = LogisticRegression(input_dim).to(device)
            optimizer = torch.optim.Adam(logistic_regression_model.parameters(), lr=learning_rate, weight_decay=lv)
            one_hot = One_Hot(10).to(device)

            print("Adam Optimiser: Learning rate=",learning_rate,"Lambda value=", lv)

            for epoch in range(n_epochs):
                train(logistic_regression_model, train_loader, one_hot, optimizer)
            accuracy = validation(logistic_regression_model, validation_loader, one_hot)
            if accuracy > best_acc:
                best_params = [learning_rate, lv]
                best_acc = accuracy

    print("Best params for Adam: learning rate =", best_params[0], "lambda =", best_params[1])

    best_acc = 0.0
    best_params = []
    for learning_rate in learning_rates:
        for lv in lambda_values:
            logistic_regression_model = LogisticRegression(input_dim).to(device)
            optimizer = torch.optim.SGD(logistic_regression_model.parameters(), lr=learning_rate, weight_decay=lv)
            one_hot = One_Hot(10).to(device)

            print("SGD Optimiser: Learning rate=", learning_rate, "Lambda value=", lv)

            for epoch in range(n_epochs):
                train(logistic_regression_model, train_loader, one_hot, optimizer)
            accuracy = validation(logistic_regression_model, validation_loader, one_hot)
            if accuracy > best_acc:
                best_params = [learning_rate, lv]
                best_acc = accuracy
    print("Best params for SGD: learning rate =", best_params[0], "lambda =", best_params[1])
    stop = timeit.default_timer()
    run_time = stop - start

    print("Total runtime=", run_time)

    return best_params, best_acc, run_time


"""Main loop. Run time and total score will be shown below."""


def run_on_dataset(dataset_name, filename):

    correct_predict, accuracy, run_time = run(logistic_regression, dataset_name, filename)

    result = OrderedDict(correct_predict=correct_predict,
                         accuracy=accuracy,
                         run_time=run_time)
    return result


def main():
    filenames = {"MNIST": "predictions_mnist.txt",
                 "CIFAR10": "predictions_cifar10.txt"}
    result_all = OrderedDict()
    best_params, best_acc, run_time = tune_hyper_parameter()
    for dataset_name in ["MNIST", "CIFAR10"]:
        result_all[dataset_name] = run_on_dataset(dataset_name, filenames[dataset_name])
    with open('result.txt', 'w') as f:
        f.writelines(pformat(result_all, indent=4))
    print("\nResult:\n", pformat(result_all, indent=4))


main()

!pip install torch