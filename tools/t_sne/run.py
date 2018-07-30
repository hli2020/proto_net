import numpy as np
import os
import torch

from wrapper import Wrapper

from sklearn import manifold, datasets
from sklearn.metrics.pairwise import pairwise_distances
from scipy.spatial.distance import squareform

import matplotlib
matplotlib.use('Agg')
from matplotlib.patches import Ellipse
import matplotlib.pyplot as plt


def preprocess(perplexity=30, metric='euclidean'):
    """ Compute pairiwse probabilities for MNIST pixels.
    """
    digits = datasets.load_digits(n_class=6)
    pos = digits.data
    y = digits.target
    n_points = pos.shape[0]
    distances2 = pairwise_distances(pos, metric=metric, squared=True)
    # This return a n x (n-1) prob array
    pij = manifold.t_sne._joint_probabilities(distances2, perplexity, False)
    # Convert to n x n prob array
    pij = squareform(pij)
    return n_points, pij, y


# PARAMS
use_v = True
draw_ellipse = True
n_topics = 2
total_ep = 500

# PREPARE DATA
n_points, _pij2d, y = preprocess()   # mnist dataset, n_points is the sample number
i, j = np.indices(_pij2d.shape)
i = i.ravel()
j = j.ravel()
pij = _pij2d.ravel().astype('float32')
# Remove self-indices
idx = i != j
i, j, pij = i[idx], j[idx], pij[idx]

print('sample number {}; topic {}'.format(n_points, n_topics))

device = 'cuda' if torch.cuda.is_available() else 'cpu'
# CREATE MODEL
if use_v:
    from vtsne import VTSNE
    model = VTSNE(n_points, n_topics, device)
    result_folder = 'results'
else:
    from tsne import TSNE
    model = TSNE(n_points, n_points)
    result_folder = 'res_not_v'
if not os.path.exists(result_folder):
    os.makedirs(result_folder)

wrap = Wrapper(model, device, epochs=1, batchsize=4096)

# PIPELINE
for itr in range(total_ep):

    wrap.fit(pij, i, j)

    # Visualize the results
    embed = model.logits.weight.cpu().data.numpy()
    f = plt.figure()

    if draw_ellipse:
        # Visualize with ellipses
        var = np.sqrt(model.logits_lv.weight.clone().exp_().cpu().data.numpy())
        ax = plt.gca()
        for xy, (w, h), c in zip(embed, var, y):
            e = Ellipse(xy=xy, width=w, height=h, ec=None, lw=0.0)
            e.set_facecolor(plt.cm.Paired(c * 1.0 / y.max()))
            e.set_alpha(0.5)
            ax.add_artist(e)
        ax.set_xlim(-9, 9)
        ax.set_ylim(-9, 9)
        plt.axis('off')
        plt.savefig(os.path.join(result_folder, 'scatter_{:03d}.png'.format(itr)), bbox_inches='tight')
        plt.close(f)

    else:
        plt.scatter(embed[:, 0], embed[:, 1], c=y * 1.0 / y.max())
        plt.axis('off')
        plt.savefig(os.path.join(result_folder, 'scatter_{:03d}.png'.format(itr)), bbox_inches='tight')
        plt.close(f)
