import pandas as pd
import matplotlib.pyplot as plt

# Function to generate graphs for HRV metrics
def generate_hrv_graphs(data_file, participants_to_compare=2):
    # Load the data
    hrv_data = pd.read_csv(data_file)

    # Select data for the specified number of participants
    participants = hrv_data["Participant"].unique()[:participants_to_compare]
    filtered_data = hrv_data[hrv_data["Participant"].isin(participants)]

    # Generate graph for RMSSD
    plt.figure(figsize=(10, 5))
    for participant in participants:
        participant_data = filtered_data[filtered_data["Participant"] == participant]
        plt.plot(
            participant_data["Segment"],
            participant_data["RMSSD"],
            marker="o",
            label=participant,
        )
    plt.title("RMSSD Over Segments")
    plt.xlabel("Segment")
    plt.ylabel("RMSSD (ms)")
    plt.legend()
    plt.grid(True)
    plt.savefig("rmssd_comparison_1.png")
    plt.show()

    # Generate graph for SDNN
    plt.figure(figsize=(10, 5))
    for participant in participants:
        participant_data = filtered_data[filtered_data["Participant"] == participant]
        plt.plot(
            participant_data["Segment"],
            participant_data["SDNN"],
            marker="o",
            label=participant,
        )
    plt.title("SDNN Over Segments")
    plt.xlabel("Segment")
    plt.ylabel("SDNN (ms)")
    plt.legend()
    plt.grid(True)
    plt.savefig("sdnn_comparison_1.png")
    plt.show()

    # Generate graph for pNN50
    plt.figure(figsize=(10, 5))
    for participant in participants:
        participant_data = filtered_data[filtered_data["Participant"] == participant]
        plt.plot(
            participant_data["Segment"],
            participant_data["pNN50"],
            marker="o",
            label=participant,
        )
    plt.title("pNN50 Over Segments")
    plt.xlabel("Segment")
    plt.ylabel("pNN50 (%)")
    plt.legend()
    plt.grid(True)
    plt.savefig("pnn50_comparison_1.png")
    plt.show()

# Path to the simulated data file
data_file = "simulated_hrv_data_with_pnn50.csv"  # Replace with the correct file path

# Generate graphs
generate_hrv_graphs(data_file)
