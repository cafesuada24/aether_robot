/* *************************************************************
   Encoder definitions
   
   Add an "#ifdef" block to this file to include support for
   a particular encoder board or library. Then add the appropriate
   #define near the top of the main ROSArduinoBridge.ino file.
   
   ************************************************************ */
   
#ifdef USE_BASE

#ifdef ROBOGAIA
  /* The Robogaia Mega Encoder shield */
  #include "MegaEncoderCounter.h"

  /* Create the encoder shield object */
  MegaEncoderCounter encoders = MegaEncoderCounter(4); // Initializes the Mega Encoder Counter in the 4X Count mode
  
  /* Wrap the encoder reading function */
  long readEncoder(int i) {
    if (i == LEFT) return encoders.YAxisGetCount();
    else return encoders.XAxisGetCount();
  }

  /* Wrap the encoder reset function */
  void resetEncoder(int i) {
    if (i == LEFT) return encoders.YAxisReset();
    else return encoders.XAxisReset();
  }
#elif defined(ARDUINO_ENC_COUNTER)
  volatile long left_enc_pos = 0L;
  volatile long right_enc_pos = 0L;
  static const int8_t ENC_STATES [] = {0,1,-1,0,-1,0,0,1,1,0,0,-1,0,-1,1,0};  //encoder lookup table
    
  /* Interrupt routine for LEFT encoder, taking care of actual counting */
  ISR (PCINT2_vect){
  	static uint8_t enc_last=0;
        
	enc_last <<=2; //shift previous state two places
	enc_last |= (PIND & (3 << 2)) >> 2; //read the current state into lowest 2 bits
  
  	left_enc_pos += ENC_STATES[(enc_last & 0x0f)];
  }
  
  /* Interrupt routine for RIGHT encoder, taking care of actual counting */
  ISR (PCINT1_vect){
        static uint8_t enc_last=0;
          	
	enc_last <<=2; //shift previous state two places
	enc_last |= (PINC & (3 << 4)) >> 4; //read the current state into lowest 2 bits
  
  	right_enc_pos += ENC_STATES[(enc_last & 0x0f)];
  }
  
  /* Wrap the encoder reading function */
  long readEncoder(int i) {
    if (i == LEFT) return left_enc_pos;
    else return right_enc_pos;
  }

  /* Wrap the encoder reset function */
  void resetEncoder(int i) {
    if (i == LEFT){
      left_enc_pos=0L;
      return;
    } else { 
      right_enc_pos=0L;
      return;
    }
  }
#elif defined(ARDUINO_SINGLE_CHANNEL_ENC_COUNTER)
  volatile uint64_t left_enc_cnt {0};
  volatile uint64_t right_enc_cnt {0};
  volatile int left_dir {1};
  volatile int right_dir {1};

  ISR (LEFT_PCINT_VECTOR) {
    left_enc_cnt += left_dir;
  }

  ISR (RIGHT_PCINT_VECTOR) {
    right_enc_cnt += right_dir;
  }

 
  
  volatile uint64_t last_left_enc_cnt {0}, last_right_enc_cnt {0};
  volatile float left_spd {0.0}, right_spd {0.0};
 

  void setDirection(int i, int dir) {
    if (i == LEFT) {
      left_dir = dir;
    } else {
      right_dir = dir;
    }
  }
  long readEncoder(int i) {
    return (i == LEFT) ? left_enc_cnt : right_enc_cnt;
  }

  void resetEncoder(int i) {
    cli();
    if (i == LEFT) {
      left_enc_cnt = 0L;
    } else {
      right_enc_cnt = 0L;
    }
    sei();
  }

  // void left_inc() {
  //   ++left_enc_cnt;
  // }

  // void right_inc() {
  //     ++right_enc_cnt;
  // }

  constexpr auto CIRCUMFERENCE { 3.14 * 0.065 };
  constexpr auto DISTANCE_PER_TICK { CIRCUMFERENCE / 40};
  
  void updateMotorSpeed() {
    left_spd = float(left_enc_cnt - last_left_enc_cnt) * DISTANCE_PER_TICK;
    right_spd = float(right_enc_cnt - last_right_enc_cnt) * DISTANCE_PER_TICK;
    last_left_enc_cnt = left_enc_cnt;
    last_right_enc_cnt = right_enc_cnt;
  }

  float getMotorSpeedMPerSec(int i) {
    if (i == LEFT) {
      return left_spd;
    } else {
      return right_spd;
    }
  }
#else
  #error A encoder driver must be selected!
#endif

/* Wrap the encoder reset function */
void resetEncoders() {
  resetEncoder(LEFT);
  resetEncoder(RIGHT);
}

#endif

