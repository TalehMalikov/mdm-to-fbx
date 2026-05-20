import numpy as np, torch, pickle, sys
sys.path.insert(0, '/home/tmalikov/motion-diffusion-model')
import utils.rotation_conversions as geometry

smpl_npy = sys.argv[1]
pkl_path = sys.argv[2]

data = np.load(smpl_npy, allow_pickle=True).item()
print('keys:', list(data.keys()), flush=True)
print('thetas shape:', data['thetas'].shape, flush=True)
print('root_translation shape:', data['root_translation'].shape, flush=True)

thetas = torch.tensor(data['thetas']).permute(2, 0, 1)
print('thetas after permute:', thetas.shape, flush=True)

rot_matrices = geometry.rotation_6d_to_matrix(thetas)
axis_angles = geometry.matrix_to_axis_angle(rot_matrices)
smpl_poses = axis_angles.numpy().reshape(-1, 72)
smpl_trans = data['root_translation'].T

print('smpl_poses shape:', smpl_poses.shape, flush=True)
print('smpl_trans shape:', smpl_trans.shape, flush=True)
print('pose sample frame 0:', smpl_poses[0, :6], flush=True)
print('trans sample:', smpl_trans[:3], flush=True)

pkl_out = {
    'smpl_poses': smpl_poses.astype('float32'),
    'smpl_trans': smpl_trans.astype('float32'),
    'smpl_scaling': [1.0]
}
pickle.dump(pkl_out, open(pkl_path, 'wb'), protocol=2)
print('pkl done', flush=True)