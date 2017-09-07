# manuscribe
Manuscribe is a graphical Python program for manually transcribing speech with the help of first-pass ASR transcripts
The input is the recipe/audio file and the corresponding ASR transcript file. 

Using AaltoASR's align command the text hypothesis will be aligned with the audio. 

After aligning you can play back the audio and the candidate word will be highlighted with a red color for each time frame,
making it easier to spot and correct falsely recongized words and phrases.

Dependencies:

Programs and libraries:
AaltoASR (align)
python-qt4
python-qt4-phonon

Optional:
Sequitur G2P (for English)

Models:
Acoustic model
Lexicon (for English)
G2P pronunciation model (for English)

Example usage from command line (Finnish):
./manuscribe.py --lang fi --align-path /home/andre/AaltoASR/bin/align --hmm models/hmms/speecon_fi_16k/speecon_mfcc_20.3.2012_20

Example usage from command line (English):
./manuscribe.py --lang en --align-path /home/andre/AaltoASR/bin/align --hmm models/hmms/wsj0_16k/wsj0_ml_pronaligned_tied1_gain3500_occ200_20.2.2010_22 --lexicon models/lm/en/gigaword_word_120000.dict --pron-model models/lm/en/gigaword_60000_pron_model --g2p-path /home/andre/g2p/g2p.py

Normal workflow in program:
1. Open Audio File or Recipe (for example finnish_test.recipe or english_test.recipe).
2. Open Transcription File (finnish_test.trn or english_test.trn).
3. Choose file from selection box in the bottom right corner.
3. Align.
4. Wait for alignment to finish.
5. Play.
6. Pause playback at any time to edit text. 
7. Resume playback after finished editing.
8. Re-align at any time to improve accuracy of alignments.
9. Finally Save Transcription File.
10. Go back to 1 or 3.

André Mansikkaniemi, andre.mansikkaniemi@aalto.fi.
