# In[1]:

from nipype import config
cfg = dict(execution={'remove_unnecessary_outputs': False})
config.update_config(cfg)

import nipype.interfaces.fsl as fsl
import nipype.interfaces.afni as afni
import nipype.interfaces.ants as ants
import nipype.interfaces.spm as spm

from nipype.interfaces.utility import IdentityInterface, Function, Select, Merge
from os.path import join as opj
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.pipeline.engine import Workflow, Node, MapNode

import numpy as np
import os, re
import matplotlib.pyplot as plt
from nipype.interfaces.matlab import MatlabCommand
MatlabCommand.set_default_paths('/Users/amr/Downloads/spm12')
MatlabCommand.set_default_matlab_cmd("matlab -nodesktop -nosplash")

# import nipype.interfaces.matlab as mlab
# mlab.MatlabCommand.set_default_matlab_cmd("matlab -nodesktop -nosplash")
# mlab.MatlabCommand.set_default_paths('/home/amr/Documents/MATLAB/toolbox/spm8')

#========================================================================================================
# In[2]:

experiment_dir = '/media/amr/Amr_4TB/NARPS/' 

# subject_list = [
#                 'sub-001', 'sub-002', 'sub-003', 'sub-004', 'sub-005', 'sub-006', 'sub-008', 'sub-009', 
#                 'sub-010', 'sub-011', 'sub-013', 'sub-014', 'sub-015', 'sub-016', 'sub-017', 'sub-018',
#                 'sub-019', 'sub-020', 'sub-021', 'sub-022', 'sub-024', 'sub-025', 'sub-026', 'sub-027', 
#                 'sub-029', 'sub-030', 'sub-032', 'sub-033', 'sub-035', 'sub-036', 'sub-037', 'sub-038', 
#                 'sub-039', 'sub-040', 'sub-041', 'sub-043', 'sub-044', 'sub-045', 'sub-046', 'sub-047', 
#                 'sub-049', 'sub-050', 'sub-051', 'sub-052', 'sub-053', 'sub-054', 'sub-055', 'sub-056', 
#                 'sub-057', 'sub-058', 'sub-059', 'sub-060', 'sub-061', 'sub-062', 'sub-063', 'sub-064', 
#                 'sub-066', 'sub-067', 'sub-068', 'sub-069', 'sub-070', 'sub-071', 'sub-072', 'sub-073', 
#                 'sub-074', 'sub-075', 'sub-076', 'sub-077', 'sub-079', 'sub-080', 'sub-081', 'sub-082', 
#                 'sub-083', 'sub-084', 'sub-085', 'sub-087', 'sub-088', 'sub-089', 'sub-090', 'sub-092', 
#                 'sub-093', 'sub-094', 'sub-095', 'sub-096', 'sub-098', 'sub-099', 'sub-100', 'sub-102', 
#                 'sub-103', 'sub-104', 'sub-105', 'sub-106', 'sub-107', 'sub-108', 'sub-109', 'sub-110', 
#                 'sub-112', 'sub-113', 'sub-114', 'sub-115', 'sub-116', 'sub-117', 'sub-118', 'sub-119', 
#                 'sub-120', 'sub-121', 'sub-123', 'sub-124'
# ]

subject_list = [ 'sub-119', 'sub-067', 'sub-089']

# subject_list = [ 'sub-001']

session_list = ['run-01',
                'run-02',
                'run-03',
                'run-04',]
                

# session_list = ['run-01',
#                 'run-04']

                
output_dir  = '/media/amr/Amr_4TB/NARPS/output_narps_proc_1st_level'
working_dir = '/media/amr/Amr_4TB/NARPS/workingdir_narps_proc_1st_level'


proc_1st_level = Workflow (name = 'proc_1st_level')
proc_1st_level.base_dir = opj(experiment_dir, working_dir)


#=====================================================================================================
# In[3]:
#to prevent nipype from iterating over the anat image with each func run, you need seperate
#nodes to select the files
#and this will solve the problem I have for almost 6 months
#but notice that in the sessions, you have to iterate also over subject_id to get the {subject_id} var



# Infosource - a function free node to iterate over the list of subject names

infosource = Node(IdentityInterface(fields=['subject_id','session_id']),
                  name="infosource")
infosource.iterables = [('subject_id', subject_list),
                       ('session_id', session_list)]


#========================================================================================================
# In[4]:
# sub-001_task-MGT_run-02_bold.nii.gz, sub-001_task-MGT_run-02_sbref.nii.gz
#/media/amr/Amr_4TB/NARPS/output_narps_preproc_preproc/preproc_img/run-04sub-119/smoothed_all_maths_filt_maths.nii.gz
#functional runs
templates = {

      'tsv_file'       : '/media/amr/Amr_1TB/NARPS/ds001205/{subject_id}/func/{subject_id}_task-MGT_{session_id}_events.tsv',
      'preproc_img'    : 'output_narps_preproc_preproc/preproc_img/{session_id}{subject_id}/smoothed_all_maths_filt_maths.nii.gz',
      'sbref_brain'    : 'output_narps_preproc_preproc/sbref_brain/{session_id}{subject_id}/{subject_id}_task-MGT_{session_id}_sbref_brain.nii.gz',
      'sbref_mask'     : 'output_narps_preproc_preproc/sbref_mask/{session_id}{subject_id}/{subject_id}_task-MGT_{session_id}_sbref_brain_mask.nii.gz',
            }



selectfiles = Node(SelectFiles(templates,
                              base_directory=experiment_dir),
                              name="selectfiles")
#========================================================================================================
# In[5]:

datasink = Node(DataSink(), name = 'datasink')
datasink.inputs.container = output_dir
datasink.inputs.base_directory = experiment_dir

substitutions = [('_subject_id_', ''),('_session_id_', '')]

datasink.inputs.substitutions = substitutions

#========================================================================================================

def create_design(tsv_file, functional_run):
            import os
            import numpy as np
            import nipype.interfaces.fsl as fsl
            from nipype.algorithms import modelgen
            from nipype.interfaces.base import Bunch

            # print(os.getcwd())
            # os.chdir('/Users/amr/Documents/events_csv_create/subj_001_session_002')


            # tsv_file = '/Users/amr/Documents/events_csv_create/subj_001_session_002/sub-001_task-MGT_run-02_events.tsv'


            data = np.genfromtxt(fname=tsv_file, delimiter="\t", skip_header=1, filling_values=1)

            gain = data[(data[:,2] - data[:,3]) > 0][:,(0,1,5)]
            np.savetxt('gain.txt', gain, delimiter='\t', fmt='%f')

            loss = data[(data[:,2] - data[:,3]) < 0][:,(0,1,5)]
            np.savetxt('loss.txt', loss, delimiter='\t', fmt='%f')

            print (gain.shape, loss.shape)

            #name of the contrasts, names of the event files

            cont1 = ('gain activation', 'T', ['gain', 'loss'], [1,0])
            cont2 = ('loss activation', 'T', ['gain', 'loss'], [0,1])
            cont3 = ('Task', 'F', [cont1, cont2])
            contrasts = [cont1, cont2, cont3]

            gain = 'gain.txt'
            loss = 'loss.txt'

            
            specify_model = modelgen.SpecifyModel()
            specify_model.inputs.input_units = 'secs'
            specify_model.inputs.functional_runs = [functional_run]
            specify_model.inputs.time_repetition = 1 #TR
            specify_model.inputs.high_pass_filter_cutoff = 90 #hpf in secs


            specify_model.inputs.event_files = [gain, loss]
            specify_model = specify_model.run()

            session_info = specify_model.outputs.session_info



            #====================================================================================================================


            level1design = fsl.model.Level1Design()
            level1design.inputs.interscan_interval = 1 #TR
            level1design.inputs.bases = {'dgamma':{'derivs': True}}

            level1design.inputs.contrasts = contrasts
            level1design.inputs.session_info = session_info
            level1design.inputs.model_serial_correlations = False

            level1design.run()


            #====================================================================================================================
            model = fsl.model.FEATModel()

            model.inputs.fsf_file = 'run0.fsf'

            model.inputs.ev_files = [gain, loss]

            model.run()

            design_file = os.path.abspath('run0.mat')
            tcon_file = os.path.abspath('run0.con')
            fcon_file = os.path.abspath('run0.fts')

            return design_file, tcon_file, fcon_file


create_design = Node(name = 'create_design',
                  interface = Function(input_names = ['tsv_file', 'functional_run'],
                                                   output_names = ['design_file', 'tcon_file', 'fcon_file'],
                  function = create_design))

#===========================================================================================================================
Film_Gls = Node(fsl.FILMGLS(), name = 'Fit_Design_to_Timeseries')
Film_Gls.inputs.threshold = 0.0
Film_Gls.inputs.smooth_autocorr = True

#===========================================================================================================================
#Estimate smootheness of the image
Smooth_Est = Node(fsl.SmoothEstimate(), name = 'Smooth_Estimation')
Smooth_Est.inputs.dof = 448 #453-5 volumes 

#===========================================================================================================================

def mask_zstats(mask_file, zstats, zfstats):
            #it is much easier to apply the masks to zstats and zfstats all inside the same function
            #rather than creating a seperate node for each one
            #plus the input is in the form of a list, which will require you to create a node select

            # fslmaths stats/zstat1 -mas mask thresh_zstat1

            #If you have many contrasts, you can create a loop and iterate over each contrast
            
            import nipype.interfaces.fsl as fsl
            import os

            mask_zstat1 = fsl.ApplyMask()
            mask_zstat1.inputs.in_file = zstats[0] 
            mask_zstat1.inputs.mask_file = mask_file
            mask_zstat1.inputs.out_file = 'thresh_zstat1.nii.gz'
            mask_zstat1.run()

            mask_zstat2 = fsl.ApplyMask()
            mask_zstat2.inputs.in_file = zstats[1] 
            mask_zstat2.inputs.mask_file = mask_file
            mask_zstat2.inputs.out_file = 'thresh_zstat2.nii.gz'
            mask_zstat2.run()


            mask_zfstat1 = fsl.ApplyMask()
            mask_zfstat1.inputs.in_file = zfstats
            mask_zfstat1.inputs.mask_file = mask_file
            mask_zfstat1.inputs.out_file = 'thresh_zfstat1.nii.gz'
            mask_zfstat1.run()

            thresh_zstat1 = os.path.abspath('thresh_zstat1.nii.gz')
            thresh_zstat2 = os.path.abspath('thresh_zstat2.nii.gz')
            thresh_zfstat1 = os.path.abspath('thresh_zfstat1.nii.gz')

            return thresh_zstat1, thresh_zstat2, thresh_zfstat1


mask_zstats = Node(name = 'mask_zstats',
                  interface = Function(input_names = ['mask_file', 'zstats', 'zfstats'],
                                                   output_names = ['thresh_zstat1', 'thresh_zstat2', 'thresh_zfstat1'],
                  function = mask_zstats))

#============================================================================================================================
#the same as previous
def clustering(thresh_zstat1, thresh_zstat2, thresh_zfstat1, copes, dlh, volume):


            #If you have many contrasts, you can create a loop and iterate over each contrast

            import nipype.interfaces.fsl as fsl
            import os

            Clustering_t1 = fsl.Cluster()
            Clustering_t1.inputs.threshold = 2.3
            Clustering_t1.inputs.pthreshold = 0.05
            Clustering_t1.inputs.in_file = thresh_zstat1
            Clustering_t1.inputs.cope_file = copes[0]
            Clustering_t1.inputs.connectivity = 26
            Clustering_t1.inputs.volume = volume
            Clustering_t1.inputs.dlh = dlh

            Clustering_t1.inputs.out_threshold_file = 'thresh_zstat1.nii.gz'
            Clustering_t1.inputs.out_index_file = 'cluster_mask_zstat1'
            Clustering_t1.inputs.out_localmax_txt_file = 'lmax_zstat1.txt'

            Clustering_t1.run()
            
            #==========================================================================================================================

            Clustering_t2 = fsl.Cluster()
            Clustering_t2.inputs.threshold = 2.3
            Clustering_t2.inputs.pthreshold = 0.05
            Clustering_t2.inputs.in_file = thresh_zstat2
            Clustering_t2.inputs.cope_file = copes[1]
            Clustering_t2.inputs.connectivity = 26
            Clustering_t2.inputs.volume = volume
            Clustering_t2.inputs.dlh = dlh

            Clustering_t2.inputs.out_threshold_file = 'thresh_zstat2.nii.gz'
            Clustering_t2.inputs.out_index_file = 'cluster_mask_zstat2'
            Clustering_t2.inputs.out_localmax_txt_file = 'lmax_zstat2.txt'

            Clustering_t2.run()

            #==========================================================================================================================
            # In[15]:
            #Clustering on the statistical output of f-contrast


            Clustering_f = fsl.Cluster()
            Clustering_f.inputs.threshold = 2.3
            Clustering_f.inputs.pthreshold = 0.05
            Clustering_f.inputs.in_file = thresh_zfstat1
            Clustering_f.inputs.connectivity = 26
            Clustering_f.inputs.volume = volume
            Clustering_f.inputs.dlh = dlh

            Clustering_f.inputs.out_threshold_file = 'thresh_zfstat1.nii.gz'
            Clustering_f.inputs.out_index_file = 'cluster_mask_zfstat1'
            Clustering_f.inputs.out_localmax_txt_file = 'lmax_zfstat1.txt'
            
            Clustering_f.run()
            thresh_zstat1 = os.path.abspath('thresh_zstat1.nii.gz')
            thresh_zstat2 = os.path.abspath('thresh_zstat2.nii.gz')
            thresh_zfstat1 = os.path.abspath('thresh_zfstat1.nii.gz')

            return thresh_zstat1, thresh_zstat2, thresh_zfstat1



clustering = Node(name = 'clustering',
                  interface = Function(input_names = ['thresh_zstat1', 'thresh_zstat2', 'thresh_zfstat1', 'copes', 'dlh', 'volume'],
                                                   output_names = ['thresh_zstat1', 'thresh_zstat2', 'thresh_zfstat1'],
                  function = clustering))

#==================================================================================================================================
#overlay the zstats over the sbref and create images to check activation 
def create_activation_pics(sbref_brain, thresh_zstat1, thresh_zstat2, thresh_zfstat1):
            import nipype.interfaces.fsl as fsl


            Overlay_t1_Contrast = fsl.Overlay()
            Overlay_t1_Contrast.inputs.background_image = sbref_brain
            Overlay_t1_Contrast.inputs.stat_image = thresh_zstat1
            Overlay_t1_Contrast.inputs.auto_thresh_bg = True
            Overlay_t1_Contrast.inputs.stat_thresh = (2.300302,12)
            Overlay_t1_Contrast.inputs.transparency = True
            Overlay_t1_Contrast.inputs.out_file = 'rendered_thresh_zstat1.nii.gz'

            Overlay_t1_Contrast.run()

            Slicer_t1_Contrast = fsl.Slicer()
            Slicer_t1_Contrast.inputs.in_file = 'rendered_thresh_zstat1.nii.gz'
            Slicer_t1_Contrast.inputs.all_axial = True
            Slicer_t1_Contrast.inputs.image_width = 750
            Slicer_t1_Contrast.inputs.out_file = 'rendered_thresh_zstat1.png'

            Slicer_t1_Contrast.run()            
            #===============================================================================

            Overlay_t2_Contrast = fsl.Overlay()
            Overlay_t2_Contrast.inputs.background_image = sbref_brain
            Overlay_t2_Contrast.inputs.stat_image = thresh_zstat1
            Overlay_t2_Contrast.inputs.auto_thresh_bg = True
            Overlay_t2_Contrast.inputs.stat_thresh = (2.300302,12)
            Overlay_t2_Contrast.inputs.transparency = True
            Overlay_t2_Contrast.inputs.out_file = 'rendered_thresh_zstat2.nii.gz'

            Overlay_t2_Contrast.run()
            
            Slicer_t2_Contrast = fsl.Slicer()
            Slicer_t2_Contrast.inputs.in_file = 'rendered_thresh_zstat2.nii.gz'
            Slicer_t2_Contrast.inputs.all_axial = True
            Slicer_t2_Contrast.inputs.image_width = 750
            Slicer_t2_Contrast.inputs.out_file = 'rendered_thresh_zstat2.png'
            
            Slicer_t2_Contrast.run()
            #===============================================================================

            Overlay_f_Contrast = fsl.Overlay()
            Overlay_f_Contrast.inputs.background_image = sbref_brain
            Overlay_f_Contrast.inputs.stat_image = thresh_zstat1
            Overlay_f_Contrast.inputs.auto_thresh_bg = True
            Overlay_f_Contrast.inputs.stat_thresh = (2.300302,12)
            Overlay_f_Contrast.inputs.transparency = True
            Overlay_f_Contrast.inputs.out_file = 'rendered_thresh_zfstat1.nii.gz'


            Overlay_f_Contrast.run()
            
            Slicer_f_Contrast = fsl.Slicer()
            Slicer_f_Contrast.inputs.in_file = 'rendered_thresh_zfstat1.nii.gz'
            Slicer_f_Contrast.inputs.all_axial = True
            Slicer_f_Contrast.inputs.image_width = 750
            Slicer_f_Contrast.inputs.out_file = 'rendered_thresh_zfstat1.png'
            
            Slicer_f_Contrast.run()
            #===============================================================================

create_activation_pics = Node(name = 'create_activation_pics',
                  interface = Function(input_names = ['sbref_brain', 'thresh_zstat1', 'thresh_zstat2', 'thresh_zfstat1'],
                                                   
                  function = create_activation_pics))







proc_1st_level.connect([


              (infosource, selectfiles, [('subject_id','subject_id'),
                                         ('session_id','session_id')]),


              (selectfiles, create_design, [('preproc_img','functional_run')]),
              (selectfiles, create_design, [('tsv_file','tsv_file')]),

              (selectfiles, Film_Gls, [('preproc_img','in_file')]),

              (create_design, Film_Gls, [('design_file','design_file'),
                                         ('tcon_file','tcon_file'),
                                         ('fcon_file','fcon_file')]),


              (selectfiles, Smooth_Est, [('sbref_brain','mask_file')]),
              (Film_Gls, Smooth_Est, [('residual4d','residual_fit_file')]),


              (selectfiles, mask_zstats, [('sbref_mask','mask_file')]),
              (Film_Gls, mask_zstats, [('zstats','zstats'),
                                       ('zfstats','zfstats')]),

              (mask_zstats, clustering, [('thresh_zstat1','thresh_zstat1'),
                                         ('thresh_zstat2','thresh_zstat2'),
                                         ('thresh_zfstat1','thresh_zfstat1')]),

              (Film_Gls, clustering, [('copes','copes')]),
              
              (Smooth_Est, clustering, [('dlh','dlh'),('volume','volume')]),

              (selectfiles, create_activation_pics, [('sbref_brain','sbref_brain')]),

              (clustering, create_activation_pics, [('thresh_zstat1','thresh_zstat1'),
                                                    ('thresh_zstat2','thresh_zstat2'),
                                                    ('thresh_zfstat1','thresh_zfstat1')]),


              (Film_Gls, datasink, [('copes','copes'),
                                    ('varcopes','varcopes')])



              ])

proc_1st_level.write_graph(graph2use='colored', format='png', simple_form=True)

proc_1st_level.run('MultiProc', plugin_args={'n_procs': 4})


