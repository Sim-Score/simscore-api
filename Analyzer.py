from typing import List
from pathlib import Path
import numpy as np
from numpy.random import RandomState
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from sklearn import manifold
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import pairwise_distances
import nltk
from nltk.corpus import stopwords, wordnet
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer


class Analyzer:
    """
    The Analyzer class is responsible for preprocessing and analyzing a list of ideas. It performs the following tasks:
    
    1. Preprocesses the ideas by normalizing the text, removing stop words, and lemmatizing the words.
    2. Embeds the preprocessed ideas using GloVe word embeddings.
    3. Calculates the cosine similarity, pairwise similarity, and pairwise distance between the embedded ideas.
    Optionally: 
        4. Generates a scatter plot visualization of the ideas based on their distance to the centroid.
        5. Generates a heatmap visualization of the pairwise similarity matrix.
        6. Generates a network graph visualization of the ideas based on their pairwise distances.
    
    The class provides a convenient `process_all()` method that runs all the analysis steps in sequence.
    """
    def __init__(self, ideas: List[str], vectorizer):
        self.processed_ideas = ideas  # these ones we modify & preprocess, i.e. remove punctuation, lemmatize etc...
        self.ideas = ideas   # these stay unmodified, but will be sorted by similarity later
        self.vectorizer = vectorizer

    def preprocess_ideas(self):
        # Ensure NLTK resources are available
        nltk.download('punkt')
        nltk.download('stopwords')
        nltk.download('wordnet')

        # Normalize words to their base form, e.g. swimming -> swim
        lemmatizer = WordNetLemmatizer()

        # Preprocess the text
        def preprocess(text):
            # Lowercase
            text = text.lower()
            # Tokenize
            tokens = word_tokenize(text)
            # Remove punctuation and stop words
            tokens = [lemmatizer.lemmatize(word) for word in tokens if word.isalpha() and word not in stopwords.words('english')]
            return ' '.join(tokens)

        self.processed_ideas = [preprocess(response) for response in self.processed_ideas]
        return self.processed_ideas

    def embedd_ideas(self):

        def load_glove_embeddings(file_path):
            embeddings_index = {}
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    values = line.split()
                    word = values[0]
                    coefs = np.asarray(values[1:], dtype='float32')
                    embeddings_index[word] = coefs
            return embeddings_index

        # Replace 'path_to_glove_file' with the path to your GloVe embeddings file
        glove_file_path = Path('glove.6B.100d.txt')
        if not glove_file_path.exists():
            return None
        embeddings_index = load_glove_embeddings(glove_file_path)

        def get_sentence_embedding(tokens, embeddings_index):
            valid_embeddings = [embeddings_index[word] for word in tokens if word in embeddings_index]
            if not valid_embeddings:
                return np.zeros(100)  # assuming the embedding size is 100
            return np.mean(valid_embeddings, axis=0)

        return np.array([get_sentence_embedding(tokens, embeddings_index) for tokens in self.processed_ideas])

    def calculate_similarities(self):
        """
        Calculates the similarities between the ideas
        
        This method uses both a vectorizer and embeddings to fits and transforms the ideas to numerical vectors.
        Both run independently and then get combined into one idea matrix. 
        
        The idea matrix is then used to calculate 
         * The 'center point' of the ideas (centroid)
         * Similarities/Distances between the ideas (pairwise) and between ideas and the centroid
        """
        # Fit and transform the ideas to numerical vectors
        vectorized_matrix = self.vectorizer.fit_transform(self.processed_ideas)
        embedded_matrix = self.embedd_ideas()
        if embedded_matrix is None:
            idea_matrix = vectorized_matrix.toarray()
        else:
            idea_matrix = np.concatenate((vectorized_matrix.toarray(), embedded_matrix), axis=1)

        # Calculate the centroid (mean) of the idea array along axis 0 (rows)
        centroid = np.mean(idea_matrix, axis=0)

        # Add the centroid as another row/column
        idea_matrix = np.vstack([idea_matrix, centroid])

        # Sort the idea_matrix based on the pairwise distances
        # we only need this temporarily to then be able to sort the idea_matrix 
        # according to which ideas _will_ be closest to the centroid. 
        # Then after sorting, we'll have to create pairwise_distances and others again.
        temp_pairwise_distance = pairwise_distances(idea_matrix, metric='cosine')
        sorted_indices = np.argsort(temp_pairwise_distance[:-1, -1])
        idea_matrix = np.concatenate((idea_matrix[sorted_indices], idea_matrix[-1:]))

        # (also make sure that we keep the order of our ideas array the same)
        self.ideas = [self.ideas[i] for i in sorted_indices]

        # Calculate similarity & distances
        # *Distances* between ideas (including the centroid), used to get the coords on the scatterplot:
        self.pairwise_distance = pairwise_distances(idea_matrix, metric='cosine')
        # *Similarity* between each idea; for the weight of the connecting lines:
        self.pairwise_similarity = cosine_similarity(idea_matrix, idea_matrix)
        
        # Similarity to centroid:
        self.cos_similarity = cosine_similarity(idea_matrix, centroid.reshape(1, -1))
        # make it so that 0 is 'same' and 1 is very different. This is used to calculate the marker size:
        self.distance_to_centroid = 1 - self.cos_similarity

    def create_scatter_plot_data(self, seed=RandomState().randint(1, 1000000)):
        # For reproducible results, set seed to a fixed number.
        mds = manifold.MDS(n_components=2, dissimilarity='precomputed', random_state=seed)
        print(seed)
        coords = mds.fit_transform(self.pairwise_distance)
        marker_sizes = self.cos_similarity
        return coords, marker_sizes

    def create_scatter_plot(self, show_plot=False):
        coords, marker_sizes = self.create_scatter_plot_data(1)
        
        def normalize(array, min_size=10, max_size=100):
            min_value = array.min()
            max_value = array.max()
            normalizedValue = (array - min_value) / (max_value - min_value)
            return min_size + normalizedValue * (max_size - min_size)
      
        # Normalize marker sizes for the plot
        normalized_marker_sizes = normalize(marker_sizes)

        fig, ax = plt.subplots(figsize=(8, 6))
        scatter = ax.scatter(coords[:, 0], coords[:, 1], c=self.distance_to_centroid, cmap='viridis', s=normalized_marker_sizes)

        # Stronger Connection Lines for stronger pairwise similarities: 
        segments = []
        line_weights = []
        for i in range(len(coords)):
            for j in range(len(coords)):
                segments.append([coords[i], coords[j]])
                line_weights.append(pow(self.pairwise_similarity[i,j], 2))

        lc = LineCollection(
            segments, zorder=0, cmap=plt.cm.Blues, norm=plt.Normalize(0, 1), linewidths=line_weights
        )
        ax.add_collection(lc)

        # Add labels to each point
        labels = []
        for i in range(len(coords)):
            if i == len(coords)-1:  # Centroid, give it a special label and size
                labels.append(ax.annotate(f"Centroid", (coords[i, 0], coords[i, 1]), xytext=(7, 3), textcoords='offset pixels'))
            else:
                text = f"{i+1}"
                label = ax.annotate(text, (coords[i, 0], coords[i, 1]), xytext=(7, 3), textcoords='offset pixels')
                labels.append(label)

        # Add a colorbar to show the mapping of colors to distances
        cbar = fig.colorbar(scatter, ax=ax)
        cbar.set_label('Distance to Centroid')

        # Set the axis labels and title
        ax.set_title('Distance to Centroid Visualization')

        if show_plot:
            # Show the plot
            plt.show()

    # Convenience shortcuts:
    def process_get_data(self):
        self.preprocess_ideas()
        self.calculate_similarities()
        coords, marker_sizes = self.create_scatter_plot_data(1)
        return coords, marker_sizes

    def process_all(self):
        self.preprocess_ideas()
        self.calculate_similarities()
        print(f"{self.vectorizer.__class__.__name__} graph:")
        self.create_scatter_plot(show_plot=False)