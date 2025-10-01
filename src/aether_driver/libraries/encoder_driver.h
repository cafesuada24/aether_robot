/* *************************************************************
   Encoder driver function definitions - by James Nugen
   ************************************************************ */
   
   
#ifdef ARDUINO_ENC_COUNTER
  //below can be changed, but should be PORTD pins; 
  //otherwise additional changes in the code are required
  #define LEFT_ENC_PIN_A PD2  //pin 2
  #define LEFT_ENC_PIN_B PD3  //pin 3
  
  //below can be changed, but should be PORTC pins
  #define RIGHT_ENC_PIN_A PC4  //pin A4
  #define RIGHT_ENC_PIN_B PC5   //pin A5
#endif

#ifdef ARDUINO_SINGLE_CHANNEL_ENC_COUNTER

  #define LEFT_ENC_PIN PD2
  #define LEFT_PCINT_VECTOR PCINT2_vect 
  #define LEFT_PCINT_MASK_REG PCMSK2
  #define LEFT_PCIE_BIT PCIE2
  
  #define RIGHT_ENC_PIN PB0
  #define RIGHT_PCINT_VECTOR PCINT0_vect 
  #define RIGHT_PCINT_MASK_REG PCMSK0
  #define RIGHT_PCIE_BIT PCIE0
#endif
   
long readEncoder(int i);
void resetEncoder(int i);
void resetEncoders();

