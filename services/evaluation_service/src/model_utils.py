import numpy as np
import torch


def get_prediction_model(ann_model_path: str) -> torch.nn.Module:
    """
    Load a PyTorch model for predictions.

    :param ann_model_path: Path to the saved PyTorch model file.
    :return: Loaded PyTorch model in evaluation mode.
    """
    # Load the model from the specified path
    model = torch.load(ann_model_path, weights_only=False)
    
    # Set the model to evaluation mode
    model.eval()
    
    return model


def get_harmony_matrix(harmony_matrix_path: str) -> np.ndarray:
    """
    Load a homography matrix from a file.

    :param harmony_matrix_path: Path to the file containing the homography matrix.
    :return: Loaded homography matrix as a NumPy array.
    """
    # Load the matrix using NumPy
    h_matrix = np.load(harmony_matrix_path)
    
    return h_matrix
