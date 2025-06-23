# Musehypothermi Python Test Suite - Final Harmonized Version
# Module: test_suite.py

from serial_comm import SerialManager
from logger import Logger
from profile_loader import ProfileLoader
from event_logger import EventLogger
import time
import argparse
import sys

class TestSuite:
    def __init__(self, port="COM3"):
        print(f"🛠️ Initializing Test Suite on port {port}...")
        self.serial = SerialManager(port)
        self.logger = Logger("test_run")
        self.event_logger = EventLogger("test_events")
        self.profile_loader = ProfileLoader()
        self.test_results = []

    def run_pid_test(self, iterations=10):
        print("\n▶️ Running PID Test")
        self.serial.sendCMD("pid", "start")
        time.sleep(1)

        success = True
        for i in range(iterations):
            data = self.serial.readData()

            if data:
                self.logger.log_data(data)
                print(f"📈 PID Data ({i+1}/{iterations}): {data}")

                rectal_temp = data.get("anal_probe_temp", None)
                if rectal_temp is None or rectal_temp < 0 or rectal_temp > 50:
                    print(f"⚠️ Warning: Rectal temperature out of range! ({rectal_temp})")
                    success = False
            else:
                print(f"❌ No data received at iteration {i+1}")
                success = False

            time.sleep(1)

        # Stop PID
        self.serial.sendCMD("pid", "stop")
        time.sleep(0.5)

        result = "PASS" if success else "FAIL"
        self.test_results.append(("PID Test", result))
        self.event_logger.log_event(f"PID test {result.lower()}.")
        print(f"✅ PID Test Complete: {result}")

    def load_and_print_profile(self, profile_path):
        print(f"\n▶️ Loading Profile: {profile_path}")
        success = self.profile_loader.load_profile_csv(profile_path)

        if success:
            self.profile_loader.print_profile()
            self.test_results.append(("Profile Load", "PASS"))
            self.event_logger.log_event("Profile loaded and printed.")
        else:
            self.test_results.append(("Profile Load", "FAIL"))
            self.event_logger.log_event("Profile load failed.")

    def run_heartbeat_test(self, duration=10):
        print(f"\n▶️ Running Heartbeat Test for {duration} seconds...")
        self.event_logger.log_event("Heartbeat test started.")

        # Start heartbeat monitoring
        start_time = time.time()
        success = True

        while time.time() - start_time < duration:
            data = self.serial.readData()

            if data:
                self.logger.log_data(data)
                print(f"💓 Heartbeat data: {data}")
            else:
                print("⚠️ No heartbeat data received!")
                success = False

            time.sleep(1)

        result = "PASS" if success else "FAIL"
        self.test_results.append(("Heartbeat Test", result))
        self.event_logger.log_event(f"Heartbeat test {result.lower()}.")

    def summary(self):
        print("\n=====================")
        print("  📝 TEST SUMMARY")
        print("=====================")
        for test, result in self.test_results:
            status = "✅" if result == "PASS" else "❌"
            print(f"{status} {test}: {result}")

    def close(self):
        print("\n🔒 Closing resources...")
        self.logger.close()
        self.event_logger.close()
        self.serial.close()
        print("✅ All resources closed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Musehypothermi Test Suite")
    parser.add_argument("--port", type=str, default="COM3", help="Serial port to connect to")
    parser.add_argument("--profile", type=str, default="profiles/hypothermia_profile_01.csv", help="Profile CSV file path")
    parser.add_argument("--iterations", type=int, default=10, help="PID test iterations")
    parser.add_argument("--heartbeat", type=int, default=0, help="Run heartbeat test (seconds)")
    parser.add_argument("--summary", action='store_true', help="Only show summary without running tests")

    args = parser.parse_args()

    test_suite = None

    try:
        test_suite = TestSuite(port=args.port)

        if args.summary:
            test_suite.summary()
            sys.exit(0)

        test_suite.load_and_print_profile(args.profile)
        test_suite.run_pid_test(iterations=args.iterations)

        if args.heartbeat > 0:
            test_suite.run_heartbeat_test(duration=args.heartbeat)

        test_suite.summary()

    except KeyboardInterrupt:
        print("\n⛔ Test aborted by user.")

    except Exception as e:
        print(f"❌ Critical error: {e}")

    finally:
        if test_suite:
            test_suite.close()
