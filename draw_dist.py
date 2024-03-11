import numpy as np
import yaml
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection


configFileName = "configs/config.yml"
with open(configFileName, "r") as stream:
    try:
        yamlConfig = yaml.safe_load(stream)
    except yaml.YAMLError as err:
        print(err)


# Read in the geometry
try:
    systemGeom = np.asarray(yamlConfig["detector geometry"])
    sensGeomIds = np.asarray(yamlConfig["detector"]["sensitive geometry indices"])
    sensGeom = systemGeom[sensGeomIds]
    detSubs = np.asarray(yamlConfig["detector"]["crystal n subdivision xyz"])
    # Calculate Image space N subdivision and size.
    imageDims = np.asarray(yamlConfig["image"]["dimension xyz"])
    imageVxpms = np.asarray(yamlConfig["image"]["voxel per mm xyz"])
    imageSubs = np.asarray(yamlConfig["image"]["subdivision xyz"])
    angle_rad = yamlConfig["image"]["detector rotation"]
    x_shift = yamlConfig["image"]["detector x-shift"]
except yaml.YAMLError as err:
    print("Error reading the configurations!", err)
    exit(1)

yMin = np.amin(systemGeom[:, 2])
yMax = np.amax(systemGeom[:, 3])
trans_x = imageDims[0] * 0.5
trans_y = imageDims[1] * 0.5
y_shift = 0.5 * (yMax - yMin)
imageNxyz = imageDims * imageVxpms
mmPerVoxel = 1.0 / imageVxpms


detectors = systemGeom[1:-1]

det_xy = np.array([detectors[:, 0], detectors[:, 2]]).T
det_inc_xy = np.array(
    [(detectors[:, 1] - detectors[:, 0]), (detectors[:, 3] - detectors[:, 2])]
).T
rect_list = [
    Rectangle(xy, inc_xy[0], inc_xy[1]) for xy, inc_xy in zip(det_xy, det_inc_xy)
]


# pA:  [-8.75 29.75  0.75]
# pB:  [12.25  8.75  0.5 ]
# Geom: [11.5 13.   8.   9.5  0.   1.  -1.  10. ]

pA = np.array([-8.75, 29.75, 0.75])
pB = np.array([12.25, 8.75, 0.5])

# Task assignment
nImgVoxels = imageNxyz.prod()
nTasks = sensGeom.shape[0] * nImgVoxels
geoms = systemGeom
o = 0.5 * (geoms[:, 0:-2:2] + geoms[:, 1:-2:2])
oa = pA - o
ob = pB - o
ab_length = np.linalg.norm(pB - pA)
dist = np.linalg.norm(np.cross(oa, ob), axis=1) / ab_length
# print(dist)
edges = geoms[:, 1:-2:2] - geoms[:, 0:-2:2]
diagLength = np.linalg.norm(0.5 * edges, axis=1)
geomsOnPath = geoms[np.where(dist < diagLength, True, False)]
geomsOnPath_xy = np.array([geomsOnPath[:, 0], geomsOnPath[:, 2]]).T
geomsOnPath_inc_xy = np.array(
    [(geomsOnPath[:, 1] - geomsOnPath[:, 0]), (geomsOnPath[:, 3] - geomsOnPath[:, 2])]
).T
geomsOnPath_list = [
    Rectangle(geomsOnPath_xy, geomsOnPath_inc_xy[0], geomsOnPath_inc_xy[1])
    for geomsOnPath_xy, geomsOnPath_inc_xy in zip(geomsOnPath_xy, geomsOnPath_inc_xy)
]


# target sensitive detector subdivision
subInc = np.array([1.5, 1, 0.5])
halfSubIncs = 0.5 * subInc
sensDetSubGeom = np.array(
    [
        pB[0] - halfSubIncs[0],
        pB[0] + halfSubIncs[0],
        pB[1] - halfSubIncs[1],
        pB[1] + halfSubIncs[1],
        pB[2] - halfSubIncs[2],
        pB[2] + halfSubIncs[2],
        -1,
        10,
    ]
)

sensDetSubGeom = np.array([11.5, 13.0, 8.0, 9.5, 0.0, 1.0, -1.0, 10.0])
nGeoms = geomsOnPath.shape[0]
if nGeoms > 0:
    geomsOnPath = np.append(geomsOnPath, sensDetSubGeom).reshape(nGeoms + 1, 8)
else:
    geomsOnPath = np.array([sensDetSubGeom])

nGeoms = geomsOnPath.shape[0]
ty = np.zeros((nGeoms, 2))
tz = ty
condition_y = np.full((nGeoms, 2), False)
condition_z = condition_y
# # Case 1: intersects on face x = x_0 or face x = x_1
# # Note that A_x never equals B_x.
# tx = (geomsOnPath[:, 0:2] - pA[0]) / (pB[0] - pA[0])
# yx = tx * (pB[1] - pA[1]) + pA[1]
# zx = tx * (pB[2] - pA[2]) + pA[2]
# condition_x = np.where(
#     (yx - np.vstack((geomsOnPath[:, 2], geomsOnPath[:, 2])).T)
#     * (yx - np.vstack((geomsOnPath[:, 3], geomsOnPath[:, 3])).T)
#     > 0,
#     False,
#     True,
# ) * np.where(
#     (zx - np.vstack((geomsOnPath[:, 4], geomsOnPath[:, 4])).T)
#     * (zx - np.vstack((geomsOnPath[:, 5], geomsOnPath[:, 5])).T)
#     > 0,
#     False,
#     True,
# )
# # Case 2: intersects on face y = y_0 or face y = y_1
# # Note: we exclude the case when A_y equals B_y
# if pB[1] - pA[1] != 0:
#     ty = (geomsOnPath[:, 2:4] - pA[1]) / (pB[1] - pA[1])
#     xy = ty * (pB[0] - pA[0]) + pA[0]
#     zy = ty * (pB[2] - pA[2]) + pA[2]
#     condition_y = np.where(
#         (xy - np.vstack((geomsOnPath[:, 0], geomsOnPath[:, 0])).T)
#         * (xy - np.vstack((geomsOnPath[:, 1], geomsOnPath[:, 1])).T)
#         > 0,
#         False,
#         True,
#     ) * np.where(
#         (zy - np.vstack((geomsOnPath[:, 4], geomsOnPath[:, 4])).T)
#         * (zy - np.vstack((geomsOnPath[:, 5], geomsOnPath[:, 5])).T)
#         > 0,
#         False,
#         True,
#     )

# # Case 3: intersects on face z = z_0 or face z = z_1
# # Note: we exclude the case when A_z equals B_z
# if pB[2] - pA[2] != 0:
#     tz = (geomsOnPath[:, 4:6] - pA[2]) / (pB[2] - pA[2])
#     xz = tz * (pB[0] - pA[0]) + pA[0]
#     yz = tz * (pB[1] - pA[1]) + pA[1]
#     condition_z = np.where(
#         (xz - np.vstack((geomsOnPath[:, 0], geomsOnPath[:, 0])).T)
#         * (xz - np.vstack((geomsOnPath[:, 1], geomsOnPath[:, 1])).T)
#         > 0,
#         False,
#         True,
#     ) * np.where(
#         (yz - np.vstack((geomsOnPath[:, 2], geomsOnPath[:, 2])).T)
#         * (yz - np.vstack((geomsOnPath[:, 3], geomsOnPath[:, 3])).T)
#         > 0,
#         False,
#         True,
#     )
# conditions = np.swapaxes(np.array([condition_x, condition_y, condition_z]), 0, 1)
# # muArr = np.repeat(geomsOnPath[:, 7], 2).reshape(geomsOnPath.shape[0], 2)
# # muArr = np.array([muArr, muArr, muArr])
# inter_list = []
# exponents = []
# tArr = np.swapaxes(np.array([tx, ty, tz]), 0, 1)
# for id in range(0, nGeoms - 1):
#     t = np.unique(tArr[id][conditions[id]])
#     t = t[np.nonzero(t < 1)]
#     if t.size > 1:
#         point1 = t[0] * (pB - pA) + pA
#         point2 = t[1] * (pB - pA) + pA
#         interception = np.linalg.norm(point1 - point2)
#         inter_list.append(t[0] * (pB - pA) + pA)
#         inter_list.append(t[1] * (pB - pA) + pA)
#         exponents.append(interception * geomsOnPath[id, 7])
# attenuationTerm = np.exp(-np.sum(exponents))


# t = tArr[-1][conditions[-1]]
# t = np.unique(t)
# try:
#     point1 = t[0] * (pB - pA) + pA
#     point2 = t[1] * (pB - pA) + pA
# except Exception as err:
#     t = np.zeros((3, 2))
#     coords = np.zeros((3, 2, 3))
#     for idx in range(0, 3):
#         t[idx, :] = (geomsOnPath[-1, idx * 2 : idx * 2 + 2] - pA[idx]) / (
#             pB[idx] - pA[idx]
#         )
#         for idy in {0,1}:
#             point=t[idx,idy]*(pB - pA)+pA
#             coords[idx,idy] = point
#     print(((coords[0,:,1]-geomsOnPath[-1,2])*(coords[0,:,1]-geomsOnPath[-1,3])<0)*((coords[0,:,1]-geomsOnPath[-1,4])*(coords[0,:,1]-geomsOnPath[-1,5])<0))
#     print(((coords[1,:,0]-geomsOnPath[-1,0])*(coords[1,:,0]-geomsOnPath[-1,1])<0)*((coords[1,:,2]-geomsOnPath[-1,4])*(coords[1,:,2]-geomsOnPath[-1,5])<0))
#     print(((coords[2,:,0]-geomsOnPath[-1,0])*(coords[2,:,0]-geomsOnPath[-1,1])<0)*((coords[2,:,1]-geomsOnPath[-1,2])*(coords[2,:,1]-geomsOnPath[-1,3])<0))
#     # ty = (geomsOnPath[-1, 4:6] - pA[2]) / (pB[2] - pA[2])
#     # tz = (geomsOnPath[-1, 4:6] - pA[2]) / (pB[2] - pA[2])
#     # xz = tz * (pB[0] - pA[0]) + pA[0]
#     # yz = tz * (pB[1] - pA[1]) + pA[1]
#     print(err, "\npB-pA: ", pB - pA, "\n", coords)
#     exit(1)


t = np.zeros((3, 2))
coords = np.zeros((3, 2, 3))
for idx in range(0, 3):
    t[idx, :] = (geomsOnPath[-1, idx * 2 : idx * 2 + 2] - pA[idx]) / (
        pB[idx] - pA[idx]
    )
    for idy in {0,1}:
        point=t[idx,idy]*(pB - pA)+pA
        coords[idx,idy] = point
print(((coords[0,:,1]-geomsOnPath[-1,2])*(coords[0,:,1]-geomsOnPath[-1,3])<=1e-10)*((coords[0,:,2]-geomsOnPath[-1,4])*(coords[0,:,2]-geomsOnPath[-1,5])<=1e-10))
print(((coords[1,:,0]-geomsOnPath[-1,0])*(coords[1,:,0]-geomsOnPath[-1,1])<=1e-10)*((coords[1,:,2]-geomsOnPath[-1,4])*(coords[1,:,2]-geomsOnPath[-1,5])<=1e-10))
print(((coords[2,:,0]-geomsOnPath[-1,0])*(coords[2,:,0]-geomsOnPath[-1,1])<=1e-10)*((coords[2,:,1]-geomsOnPath[-1,2])*(coords[2,:,1]-geomsOnPath[-1,3])<=1e-10))
print(coords[0,0])
print(coords[0,0])
print(coords[1,0])
print(coords[1,1])
# interception = np.linalg.norm(point1 - point2)
# absorptionTerm = 1 - np.exp(-interception * geomsOnPath[-1, 7])
# # print(np.linalg.norm(point1 - point2))
# inter_list.append(t[0] * (pB - pA) + pA)
# inter_list.append(t[1] * (pB - pA) + pA)


# sensDetSubAreas = np.array(
#     [
#         subInc[1] * subInc[2],
#         subInc[0] * subInc[2],
#         subInc[0] * subInc[1],
#     ]
# )
# solidAngleTerm = np.sum(np.abs(pB - pA) * sensDetSubAreas) / (  
#     ab_length**3 * 4.0 * np.pi
# )

# print("Attenuation Term: ", attenuationTerm)
# print("Absorption  Term: ", absorptionTerm)
# print("Solid Angle Term: ", solidAngleTerm)
# print("Product:          ", attenuationTerm * absorptionTerm * solidAngleTerm)

# print(np.abs(t[1]-t[0])*ab_length)
# print(np.array(inter_list))
# inter_x = np.array(inter_list)[:, 0]
# inter_y = np.array(inter_list)[:, 1]
inter_x=np.array([11.5,13])
inter_y=np.array([9.5,8])
# print(inter_x)
# print(inter_y)
target = sensDetSubGeom
target_xy = [target[0], target[2]]
target_inc_xy = [target[1] - target[0], target[3] - target[2]]
target_rect = plt.Rectangle(
    target_xy, target_inc_xy[0], target_inc_xy[1], color="yellow", ec="black"
)

pC=(pB-pA)*2+pA
# # Geometries on the gamma ray path
# geomsOnPath = geoms[np.where(dist < diagLength, True, False)]
fig, ax = plt.subplots(figsize=(10, 6))
# target_rect=plt.Rectangle(pB[0:2]-halfSubIncs[0:2],2*halfSubIncs[0],2*halfSubIncs[1],color='r')
# ax[0].add_patch(target_rect)
ax.set_aspect("equal")
pc = PatchCollection(rect_list, ec="black")
pc2 = PatchCollection(geomsOnPath_list, ec="black", fc="r")
ax.add_collection(pc)
ax.add_collection(pc2)
ax.add_patch(target_rect)
ax.scatter([pA[0], pB[0]], [pA[1], pB[1]], fc="black")
ax.plot([pA[0], pC[0]], [pA[1], pC[1]], color="black")
ax.scatter(inter_x, inter_y, color="b")
# target_rect=plt.Rectangle(pB[0::2]-halfSubIncs[0::2],2*halfSubIncs[0],2*halfSubIncs[2],color='b')
# ax[1].add_patch(target_rect)
# ax[1].set_aspect('equal')
# ax[1].scatter([pA[0],pB[0]],[pA[2],pB[2]])
# ax[1].plot([pA[0],pB[0]],[pA[2],pB[2]])
# fig.savefig("plot.png")
plt.show()
