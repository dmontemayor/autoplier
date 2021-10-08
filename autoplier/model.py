import pandas as pd
import numpy as np

from tensorflow.random import set_seed
from tensorflow.math import reduce_max, reduce_sum, square
from tensorflow.keras.layers import Input, Dense, Dropout, PReLU, LeakyReLU, BatchNormalization
from tensorflow.keras.initializers import Constant
from tensorflow.keras.regularizers import l1
from tensorflow.keras.models import Model
from tensorflow.keras.callbacks import EarlyStopping, LambdaCallback


def set_seed_(seed):
    np.random.seed(seed)  # numpy seed
    set_seed(seed)  # tensorflow seed


class autoPLIER:

    def __init__(self, n_inputs, n_components=100, dropout_rate=0.09, regval=1.20E-3, alpha_init=.05):

        # - - - - - - Model Arch  - - - - - -
        # visible is the input data
        self.visible = Input(shape=(n_inputs,))

        # define a dense single layer (Ulayer) with L1 regularization to encourage sparsity
        # ulayer = Dense(nz, kernel_regularizer=l1(regval), activation="relu", name="ulayer")
        self.ulayer = Dense(n_components, kernel_regularizer=l1(regval), name="ulayer")

        # foward pass the input through the ulayer
        self.encoder = self.ulayer(self.visible)

        # Normalize the encoder output
        self.encoder = BatchNormalization()(self.encoder)  # not necessary in our case.

        # Apply a PReLU type activation to constrain for positive weights
        # Logistic activation may also be a viable choice here - should give standardized
        #   latent variable values so we can skip a post-processing step.
        self.encoder = PReLU(alpha_initializer=Constant(value=alpha_init),
                             alpha_regularizer='l1')(self.encoder)

        # Apply Dropout to encourage parsimony (ulayer sparsity)
        self.encoder = Dropout(dropout_rate)(self.encoder)

        # The decoder does not have to be symmetric with encoder but let's have L1 reg anyway
        self.decoder = Dense(n_inputs, kernel_regularizer=l1(regval))(self.encoder)

        self.decoder = BatchNormalization()(self.decoder)

        # Apply a ReLU type activation
        self.decoder = LeakyReLU()(self.decoder)

        # Apply the same Dropout as in the encoder
        self.decoder = Dropout(dropout_rate)(self.decoder)

        # - - - - - - Build Model - - - - - -
        self.model = Model(inputs=self.visible, outputs=self.decoder)

        # Define a forbenius metric for the Latent variables to compare with paper
        self.model.add_metric(reduce_sum(square(self.encoder)), name='magz')

        # compile autoencoder model - with adam opt and use mse as reconstruction error
        self.model.compile(optimizer='adam', loss='mse')

    # - - - - - - Model Training  - - - - - -
    def fit(self, x_train, callbacks =[], batch_size=50, maxepoch=2000, verbose=2, valfrac=.3):

        # fit the autoencoder model to reconstruct input
        history = self.model.fit(x_train, x_train, epochs=maxepoch, batch_size=batch_size, verbose=verbose,
                                 validation_split=valfrac, callbacks=callbacks)
        return history

    # - - - - - - Build Encoder Model - - - - - -
    def build_encoder(self):

        # define an encoder model (without the decoder)
        self.final_encoder = Model(inputs=self.visible, outputs=self.encoder)

        # compile encoder model- with adam opt and use mse as reconstruction error
        self.final_encoder.compile(optimizer='adam', loss='mse')

    def transform(self, x_predict, index):
        z_predicted = pd.DataFrame(self.final_encoder.predict(x_predict), index=index)

        return z_predicted

    def fit_transform(self, x_train, index, callbacks=[], batch_size=50, maxepoch=2000, verbose=2, valfrac=.3):
        # fit the autoencoder model to reconstruct input
        self.model.fit(x_train, x_train, epochs=maxepoch, batch_size=batch_size, verbose=verbose,
                                 validation_split=valfrac, callbacks=callbacks)

        # define an encoder model (without the decoder)
        self.final_encoder = Model(inputs=self.visible, outputs=self.encoder)

        # compile encoder model- with adam opt and use mse as reconstruction error
        self.final_encoder.compile(optimizer='adam', loss='mse')
        z_predicted = pd.DataFrame(self.final_encoder.predict(x_train), index=index)

        return z_predicted
