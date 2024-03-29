import numpy as np
import sys
from math import floor
from keras.models import Sequential, Model, load_model
from keras.layers import LSTM, Input, Dense, Dropout

class Network:
    """A class representing a neural network utilising an LSTM seq2seq.

       We use an encoder-decoder model, adapted from those used for machine
       translation. An encoder takes in input in the form of a section
       of the piano roll, and outputs its internal state. The decoder
       then takes this internal state, and is trained to predict the 
       next section of music, using teacher forcing. Finally, we use the 
       trained decoder, coupled with a primer to generate music.

       By default, we use 2 bars of 4/4 music (8 beats).
    """

    def __init__(self, midi_in, beats_in_window=8):
        self.encoder_in_data = np.array(midi_in.beat_roll)
        self.midi_in = midi_in

        # The total number of slices in the context window
        #  is the beats multiplied by how many slices are in a beat
        self.time_step = beats_in_window * midi_in.res
        total_beats = midi_in.total_ticks / midi_in.tpb
        self.beats_in_window = beats_in_window
        self.N = floor((total_beats / beats_in_window)) - 1
 
        self.X = np.zeros(shape=(self.N, self.time_step, midi_in.note_range))
        self.y = np.zeros(shape=(self.N, self.time_step, midi_in.note_range))

        for i in range(0, self.N):
            beat_start = i * self.time_step
            self.X[i] = midi_in.beat_roll[beat_start:beat_start + self.time_step]
            
            if i > 0:
                self.y[i - 1] = midi_in.beat_roll[beat_start + self.time_step:beat_start + self.time_step * 2]
        
        self.hidden = 128

        # Stacked LSTM encoder
        # We define the encoder inputs to be a 2d window with length defined by the
        # resolution of the midi and how many bars we want, and height as the range of
        # notes
        self.enc_in = Input(shape=(self.time_step, midi_in.note_range), name='encoder_input')

        self.enc_lstm_1 = LSTM(self.hidden, return_sequences=True, name='encoder_lstm_input')
        enc_out = self.enc_lstm_1(self.enc_in)
        enc_out = Dropout(0.3)(enc_out)

        self.enc_lstm_2 = LSTM(self.hidden, return_state=True, name='encoder_lstm_output')
        enc_out, enc_h, enc_c = self.enc_lstm_2(enc_out)
        self.enc_state = [enc_h, enc_c]

        # Stacked LSTM Decoder
        self.dec_in = Input(shape=(self.time_step, midi_in.note_range), name='decoder_input')
        self.dec_lstm_1 = LSTM(self.hidden, return_sequences=True, name='decoder_lstm_input')
        dec_out = self.dec_lstm_1(self.dec_in, initial_state=self.enc_state)
        self.dec_lstm_2 = LSTM(self.hidden, return_sequences=True, return_state=True, name='decoder_lstm_output')
        dec_out, _, _ = self.dec_lstm_2(dec_out)

        self.dec_dense = Dense(midi_in.note_range, activation='softmax', name='decoder_dense')
        dec_out = self.dec_dense(dec_out)

        self.training_model = Model(inputs=[self.enc_in, self.dec_in], outputs=[dec_out])
        

    def train(self, epochs=50):
        # Since we're doing multi-label classification instead of multiclass,
        # we use binary cross entropy loss
        self.training_model.compile(optimizer='rmsprop', loss='binary_crossentropy')
        self.training_model.fit([self.X, self.X], self.y, batch_size=1, epochs=epochs, validation_split=0.2)
    
    '''
    def compose(self, length=1, initial=None):
        # Create inference model
        enc = Model(self.enc_in, self.enc_state)
        
        dec_state_in = [Input(shape=(self.hidden,)), Input(shape=(self.hidden,))]

        dec_out = self.dec_lstm_1(self.dec_in, initial_state=dec_state_in)
        dec_out, dec_h, dec_c = self.dec_lstm(dec_out)
        dec_state_out = [dec_h, dec_c]
        dec_out = self.dec_dense(dec_out)
        dec_model = Model([self.dec_in] + dec_state_in,
                          [dec_out] + dec_state_out)
        
        if initial == None:
            initial = np.random.randint(0, len(self.X) - 1)

        initial_X = self.X[initial].reshape(1, self.X.shape[1], self.X.shape[2])
        states = enc.predict(initial_X)

        target_seq = initial_X
        
        song = np.zeros(shape=initial_X.shape)
        song = [np.zeros(shape=initial_X.shape) for _ in range(length)]
        for i in range(length):
            output, h, c = dec_model.predict([target_seq] + states)
            song[i] = output[0]

            target_seq = output 
            states = [h, c]
        
        song = np.array(song)

        return song.reshape(song.shape[0] * song.shape[1], song.shape[2])
    '''


    def save(self, filename):
        self.training_model.save(filename)

    
    def load_training(self, filename):
        self.training_model = load_model(filename)

