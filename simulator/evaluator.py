from simulator import simulator
from simulator import steering

from tqdm import tqdm
from .transformation import *
from simulator.transformation import Crop
from util.reader import Reader, JSONReader


class AugmentationEvaluator:
    def __init__(self, reader: Reader, translation_threshold=1.5, rotation_threshold=0.2, time_penalty=6, frame_rate=3):
        """
        :param json: path to json file
        :param translation_threshold: translation threshold on OX axis
        :param rotation_threshold: rotation threshold relative to OY axis
        :param time_penalty: time penalty for human intervention
        """
        self.reader = reader
        self.translation_threshold = translation_threshold
        self.rotation_threshold = rotation_threshold
        self.time_penalty = time_penalty
        self.frame_rate = frame_rate
        self.frame_idx = 0

        # initialize simulator
        self.simulator = simulator.Simulator(
            reader=reader,
            time_penalty=self.time_penalty,
            distance_limit=self.translation_threshold,
            angle_limit=self.rotation_threshold
        )

        # set transformation matrix
        self.T = np.eye(3)

        # initialize trajectory buffers
        self.trajectories = {
            "real_trajectory": [],
            "sim_trajectory": [],
        }

        # initailize intervention points buffers
        self.interv_points = {
            "northing": [],
            "easting": [],
        }
        

    def get_trajectories(self):
        return self.trajectories

    def get_intervention_points(self):
        return self.interv_points

    @staticmethod
    def get_relative_course(prev_course, crt_course):
        a = crt_course - prev_course
        a = (a + 180) % 360 - 180
        return a

    @staticmethod
    def get_rotation_matrix(course):
        rad_course = -np.deg2rad(course)
        R = np.array([
            [np.cos(rad_course), -np.sin(rad_course), 0],
            [np.sin(rad_course), np.cos(rad_course), 0],
            [0, 0, 1]
        ])
        return R

    @staticmethod
    def get_translation_matrix(position):
        T = np.eye(3)
        T[0, 2] = position[0]
        T[1, 2] = position[1]
        return T

    @property
    def statistics(self):
        return self.simulator.get_statistics()

    def reset(self):
        self.packet = self.reader.get_next_image()
        frame, speed, rel_course = self.packet
        
        dt = 1.0 / self.reader.frame_rate
        R = steering.get_radius_from_course(rel_course, speed, dt)
        turning = 1 / R
        
        # process frame
        frame = self.process_frame(frame)
        return frame, speed, turning, False

    def process_frame(self, frame):
        frame = self.reader.crop_car(frame)
        frame = self.reader.crop_center(frame)
        frame = self.reader.resize_img(frame)
        return frame

    def step(self, pred_turning=0.):
        """
        :param predicted_course: predicted course by nn in degrees
        :return: augmented image corresponding to predicted course or empty np.array in case the video ended
        """
        next_packet = self.reader.get_next_image()
        if len(next_packet[0]) == 0:
            return np.array([]), None, None, None

        # compute steering from course, speed, dt
        frame, speed, rel_course = self.packet
        dt = 1.0 / self.reader.frame_rate

        # get real steering
        steer = steering.get_steer_from_course(rel_course, speed, dt)

        # get predicted steering
        sgn = 1 if pred_turning >= 0 else -1
        pred_R = sgn / (abs(pred_turning) + 1e-5)
        pred_delta, _, _ = steering.get_delta_from_radius(pred_R)
        pred_steer = steering.get_steer_from_delta(pred_delta)

        # augment the view
        next_frame = next_packet[0]
        args = [next_frame, steer, speed, dt, pred_steer]
        next_sim_frame, interv = self.simulator.run(args)

        # trajectory book keeping
        real_position = np.array([
               self.reader.easting - self.reader.init_easting,
               self.reader.northing - self.reader.init_northing,
        ])

        # compute sim car relative position
        relative_position = np.array([self.simulator.get_distance(), 0, 1])
        R = AugmentationEvaluator.get_rotation_matrix(self.reader.course)
        sim_position = real_position + np.dot(R, relative_position)[:-1]

        # append coordinates to trajectory dictionary/buffers
        self.trajectories["real_trajectory"].append(real_position)
        self.trajectories["sim_trajectory"].append(sim_position)
        

        # update packet
        self.packet = next_packet

        # if intervention happened
        if interv:
            # append intervention point (relative to UPB map)
            self.interv_points["easting"].append(
                sim_position[0] + self.reader.init_easting
            )
            self.interv_points["northing"].append(
                sim_position[1] + self.reader.init_northing
            )

            # return the ground truth info
            frame, speed, rel_course = self.packet
            R = steering.get_radius_from_course(rel_course, speed, dt)
            turning  = 1 / R

            frame = self.process_frame(frame) 
            return frame, speed, turning, True

        # update the frame with the simulated one
        self.packet = (next_sim_frame, *self.packet[1:])

        # update the new view
        frame, speed, rel_course = self.packet
        R = steering.get_radius_from_course(rel_course, speed, dt)
        turning = 1 / R

        # process the image
        frame = self.process_frame(frame)
        return frame, speed, turning, False

    @property
    def video_length(self):
        return self.reader.video_length

    @property
    def autonomy(self):
        total_time = self.video_length
        return self.simulator.get_autonomy(total_time=total_time)

    @property
    def number_interventions(self):
        return self.simulator.get_number_interventions()


if __name__ == "__main__":
    # initialize evaluator
    # check multiple parameters like time_penalty, distance threshold and angle threshold
    # in the original paper time_penalty was 6s
    reader = JSONReader("/home/robert/PycharmProjects/upb_dataset/", "0a470a2597ef4d05.json", 3)
    # reader = PKLReader("/home/robert/PycharmProjects/upb_dataset_new/video1", "metadata.pkl", 3)
    augm = AugmentationEvaluator(reader, time_penalty=6)
    predicted_course = 0.0

    # get first frame of the video
    frame, speed = augm.reset()

    # while True:
    for i in tqdm(range(100)):
        # make prediction based on frame
        # predicted_course = 0.01 * np.random.randn(1)[0]
        predicted_course = -0.1 * np.random.rand(1)[0]

        # get next frame corresponding to current prediction
        frame, speed, _ = augm.step(predicted_course)
        if frame.size == 0:
            break

        # show augmented frmae
        cv2.imshow("Augmented frame", frame)
        cv2.waitKey(0)

    print(reader.video_length)
    # print autonomy and number of interventions
    print("Autonomy:", augm.autonomy)
    print("#Interventions:", augm.number_interventions)
