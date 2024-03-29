import torch
import random
import scipy.io
import numpy as np
from sklearn import cluster

def Adjacency_KNN(fc_data: np.ndarray, k=5):
    if k == 0:
        return np.copy(fc_data)
    adjacency = np.zeros(fc_data.shape)
    for subject_idx, graph in enumerate(fc_data):
        topk_idx = np.argsort(graph)[:, -1:-k-1:-1]
        for row_idx, row in enumerate(graph):
            adjacency[subject_idx, row_idx, topk_idx[row_idx]] = row[topk_idx[row_idx]]
        adjacency[subject_idx] = adjacency[subject_idx] + adjacency[subject_idx].T
    return adjacency

def Binary_adjacency(cor_adjacency: np.array):
    bi_adjacency = np.zeros(cor_adjacency.shape)
    for subject_idx, graph in enumerate(cor_adjacency):
        for row in range(graph.shape[0]):
            for col in range(graph.shape[1]):
                bi_adjacency[subject_idx][row][col] = 1 if graph[row][col] != 0 else 0
    return bi_adjacency

def load_data(root, name, modality='fmri'):
    file = scipy.io.loadmat(f'{root}/{name}.mat')
    labels = torch.Tensor(file['label']).long().flatten()
    if name in ['HIV','BP']:
        data = file[modality].transpose(2,0,1)
    elif name == 'PPMI':
        X = file['X']
        data = np.zeros((X.shape[0], 84, 84))
        if modality == 'dti':
            model_index = 2
        else:
            model_index = int(modality)

        for (index, sample) in enumerate(X):
            data[index, :, :] = sample[0][:, :, model_index]
    else:
        data = file[modality]
    data = normalization(data)
    labels[labels == -1] = 0
    cor_adj = Adjacency_KNN(data)
    bi_adj = Binary_adjacency(cor_adj)
    return torch.Tensor(data), torch.Tensor(bi_adj), torch.Tensor(labels)

def getEdgeIdxAttr(adj):
    assert adj.dim() >= 2 and adj.dim() <= 3
    assert adj.size(-1) == adj.size(-2)

    index = adj.nonzero(as_tuple=True)
    edge_attr = adj[index]

    return torch.stack(index, dim=0), edge_attr

def adjust_learning_rate(optimizer, epoch, learning_rate, lrdec_1=0.5, lrdec_2=10):
    lr = learning_rate * (lrdec_1 ** (epoch // lrdec_2))
    for param_group in optimizer.param_groups:
        param_group['lr'] = lr   

def binaryPartition(anchor, negSample, k=2):
        k_means = cluster.KMeans(k, init=kmeans_plus(negSample, 2, anchor, random_state=42), n_init=1)
        k_means.fit(negSample)
        return k_means

def kmeans_plus(X, n_clusters, fc, random_state=42):
    np.random.seed(random_state)
    centroids = [fc]
    i = 0
    for _ in range(1, n_clusters):
        dist_sq = np.array([min([np.inner(c-x,c-x) for c in centroids]) for x in X])
        probs = dist_sq/dist_sq.sum()
        cumulative_probs = probs.cumsum()
        r = np.random.rand()
        
        for j, p in enumerate(cumulative_probs):
            if r < p:
                i = j
                break        
        centroids.append(X[i])
    return np.array(centroids)

def normalization(data):
    new_data = np.zeros_like(data)
    for index in range(len(data)):
        new_data[index] = (data[index] - np.mean(data[index])) / np.std(data[index])
    return new_data

def setup_seed(seed):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    np.random.seed(seed)
    random.seed(seed)
 