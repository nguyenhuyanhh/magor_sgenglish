export PATH=$KALDI_ROOT/tools/irstlm/bin:$PATH
export PATH=$KALDI_ROOT/tools/sph2pipe_v2.5:$PATH
export PATH=$KALDI_ROOT/tools/sctk/bin:$PATH
export PATH=$KALDI_ROOT/tools/openfst/bin:$KALDI_ROOT/src/fstbin/:$PATH

export SEQUITUR=$KALDI_ROOT/tools/sequitur
export PATH=$PATH:${SEQUITUR}/bin
_site_packages=`find ${SEQUITUR}/lib -type d -regex '.*python.*/site-packages'`
export PYTHONPATH=$PYTHONPATH:$_site_packages
export G2P_MODEL=${SEQUITUR}/models/TED-M5.pic

export PATH=\
$KALDI_ROOT/src/bin:$KALDI_ROOT/src/chainbin:\
$KALDI_ROOT/src/featbin:$KALDI_ROOT/src/fgmmbin:\
$KALDI_ROOT/src/fstbin:$KALDI_ROOT/src/gmmbin:\
$KALDI_ROOT/src/ivectorbin:$KALDI_ROOT/src/kwsbin:\
$KALDI_ROOT/src/latbin:$KALDI_ROOT/src/lmbin:\
$KALDI_ROOT/src/nnet2bin:$KALDI_ROOT/src/nnet3bin:\
$KALDI_ROOT/src/nnetbin:$KALDI_ROOT/src/online2bin:\
$KALDI_ROOT/src/onlinebin:$KALDI_ROOT/src/sgmm2bin:\
$KALDI_ROOT/src/sgmmbin:$PATH

export PATH=$lvcsrRootDir/scripts:$lvcsrRootDir/scripts/utils:$lvcsrRootDir/scripts/steps:$PATH
export LC_ALL=C
