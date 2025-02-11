import pandas as pd
import matplotlib.pyplot as plt
import os


def generate_hrv_graphs(data_file, participants_per_group=2):
    # Load the data
    hrv_data = pd.read_csv(data_file)

    # Get unique participants
    participants = hrv_data["Participant"].unique()

    # Create the base folder
    base_folder = "group_graphs"
    os.makedirs(base_folder, exist_ok=True)

    # Iterate through participants in groups
    group_number = 1
    for i in range(0, len(participants), participants_per_group):
        group_participants = participants[i:i + participants_per_group]
        group_folder = os.path.join(base_folder, f"group_{group_number}")
        os.makedirs(group_folder, exist_ok=True)

        # Filter data for the current group
        filtered_data = hrv_data[hrv_data["Participant"].isin(group_participants)]

        # Generate graph for RMSSD
        plt.figure(figsize=(10, 5))
        for participant in group_participants:
            participant_data = filtered_data[filtered_data["Participant"] == participant]
            plt.plot(
                participant_data["Segment"],
                participant_data["RMSSD"],
                marker="o",
                label=participant,
            )
        plt.title(f"Group {group_number} - RMSSD Over Segments")
        plt.xlabel("Segment")
        plt.ylabel("RMSSD (ms)")
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join(group_folder, f"rmssd_group_{group_number}.png"))
        plt.close()

        # Generate graph for SDNN
        plt.figure(figsize=(10, 5))
        for participant in group_participants:
            participant_data = filtered_data[filtered_data["Participant"] == participant]
            plt.plot(
                participant_data["Segment"],
                participant_data["SDNN"],
                marker="o",
                label=participant,
            )
        plt.title(f"Group {group_number} - SDNN Over Segments")
        plt.xlabel("Segment")
        plt.ylabel("SDNN (ms)")
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join(group_folder, f"sdnn_group_{group_number}.png"))
        plt.close()

        # Generate graph for pNN50
        plt.figure(figsize=(10, 5))
        for participant in group_participants:
            participant_data = filtered_data[filtered_data["Participant"] == participant]
            plt.plot(
                participant_data["Segment"],
                participant_data["pNN50"],
                marker="o",
                label=participant,
            )
        plt.title(f"Group {group_number} - pNN50 Over Segments")
        plt.xlabel("Segment")
        plt.ylabel("pNN50 (%)")
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join(group_folder, f"pnn50_group_{group_number}.png"))
        plt.close()

        group_number += 1


# Path to the simulated data file
data_file = "hrv_values.csv"
generate_hrv_graphs(data_file)
