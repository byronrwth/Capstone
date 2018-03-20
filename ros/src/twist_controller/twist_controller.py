from yaw_controller import YawController
from lowpass import LowPassFilter
from pid import PID

import rospy

GAS_DENSITY = 2.858
ONE_MPH = 0.44704


class Controller(object):
    def __init__(self, *args, **kwargs):
        self.throttle_control = PID(
                                kp = 3.0,
                                ki = 2.4,
                                kd = 1.0,
                                mn = -1.0,
                                mx = 1.0)

        self.steer_control = PID(
                                kp=1.0,
                                ki=0.0,
                                kd=0.05)

        self.steering_control = YawController(kwargs['wheel_base'], kwargs['steer_ratio'],
                                         kwargs['min_speed'], kwargs['max_lat_accel'],
                                         kwargs['max_steer_angle']
                                         )
                                         
        self.time = None
        self.max_vel = kwargs['max_vel']
        self.accel_limit = kwargs['accel_limit']
        self.decel_limit = kwargs['decel_limit']
        self.TP1_throttle = LowPassFilter(0.5, 0.1)
        self.linear_pid = PID(kp=0.8, ki=0, kd=0.05, mn=self.decel_limit, mx=0.5 * self.accel_limit)

        #self.vehicle_mass = kwargs['vehicle_mass']
        #self.fuel_capacity = kwargs['fuel_capacity']
        #self.wheel_radius = kwargs['wheel_radius']
        #self.brake_deadband = kwargs['brake_deadband']


    def control(self, *args, **kwargs):
        #linear_velocity = kwargs['linear_velocity']
        #angular_velocity = kwargs['angular_velocity']
        #current_velocity = kwargs['current_velocity']
                
        linear_velocity = kwargs['target_linear_velocity']
        angular_velocity = kwargs['target_angular_velocity']
        current_velocity = kwargs['current_linear_velocity']

        dbw_state = kwargs['dbw_state']

        # when needs slow down
        #if linear_velocity < current_velocity:
        #    rospy.logwarn("twist_controller.py: control(): target linear v = " + str(linear_velocity) + " ,current linear v=" +str(current_velocity))
        rospy.logwarn("twist_controller.py: control(): target v = " + str(linear_velocity) + " ,current v=" +str(current_velocity))


        if self.time is None or not dbw_state:
            self.time = rospy.get_time()
            return 0.0, 0.0, 0.0
            
        dt = rospy.get_time() - self.time

        #velocity_margin = min(linear_velocity.x, self.max_vel) - current_velocity.x
        velocity_margin = min(linear_velocity, self.max_vel) - current_velocity
        # Incorporate Acceleration and Deceleration Limits
        velocity_margin = min(velocity_margin, self.accel_limit * dt)
        velocity_margin = max(velocity_margin, self.decel_limit * dt)
        
        throttle = self.throttle_control.step(velocity_margin, dt)
        #rospy.logwarn("twist_controller.py: control(): throttle_control: throttle = " + str(throttle) )

        #steer = self.steering_control.get_steering(linear_velocity.x, angular_velocity.z, current_velocity.x)
        steer = self.steering_control.get_steering(linear_velocity, angular_velocity, current_velocity)
        steer = self.steer_control.step(steer, dt)

        throttle_1 = self.TP1_throttle.filt(throttle)
        #rospy.logwarn("twist_controller.py: control(): TP1_throttle: throttle = " + str(throttle) )

        linear_velocity_error = linear_velocity - current_velocity

        velocity_correction = self.linear_pid.step(linear_velocity_error, 3.0 #duration_in_seconds
            )

        throttle_2 = velocity_correction

        throttle = throttle_1
        #throttle = throttle_2
        #if linear_velocity_error < 0:
        #    rospy.logwarn("twist_controller.py: control(): linear_velocity_error = "+str(linear_velocity_error)+" ,velocity_correction = " + str(throttle_2))

        # we need throttle can be minus, i.e. < 0, when car needs slow down
        if throttle < 0:
            deceleration = abs(throttle)
            throttle = 0.0
            #brake = -throttle
            brake = 100
        else: #throttle >= 0:
            brake = 0.0
        
        self.time = rospy.get_time()
        return throttle, brake, steer
