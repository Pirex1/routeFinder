#include <Arduino.h>
#include <Adafruit_ILI9341.h>
#include <SD.h>
#include "consts_and_types.h"
#include "map_drawing.h"
#include <string.h>


// the variables to be shared across the project, they are declared here!
shared_vars shared;

Adafruit_ILI9341 tft = Adafruit_ILI9341(clientpins::tft_cs, clientpins::tft_dc);

enum {WAIT_FOR_START,SEND_REQ,WAIT_FOR_ACK,SEND_DATA,RECIEVE_DATA,WAIT_FOR_STOP} curr_mode = WAIT_FOR_START;

void setup() {
  // initialize Arduino
  init();

  // initialize zoom pins
  pinMode(clientpins::zoom_in_pin, INPUT_PULLUP);
  pinMode(clientpins::zoom_out_pin, INPUT_PULLUP);

  // initialize joystick pins and calibrate centre reading
  pinMode(clientpins::joy_button_pin, INPUT_PULLUP);
  // x and y are reverse because of how our joystick is oriented
  shared.joy_centre = xy_pos(analogRead(clientpins::joy_y_pin), analogRead(clientpins::joy_x_pin));

  // initialize serial port
  Serial.begin(9600);
  Serial.flush(); // get rid of any leftover bits

  // initially no path is stored
  shared.num_waypoints = 0;

  // initialize display
  shared.tft = &tft;
  shared.tft->begin();
  shared.tft->setRotation(3);
  shared.tft->fillScreen(ILI9341_BLUE); // so we know the map redraws properly

  // initialize SD card
  if (!SD.begin(clientpins::sd_cs)) {
      Serial.println("Initialization has failed. Things to check:");
      Serial.println("* Is a card inserted properly?");
      Serial.println("* Is your wiring correct?");
      Serial.println("* Is the chipSelect pin the one for your shield or module?");

      while (1) {} // nothing to do here, fix the card issue and retry
  }

  // initialize the shared variables, from map_drawing.h
  // doesn't actually draw anything, just initializes values
  initialize_display_values();

  // initial draw of the map, from map_drawing.h
  draw_map();
  draw_cursor();

  // initial status message
  status_message("FROM?");
}

void process_input() {
  // read the zoom in and out buttons
  shared.zoom_in_pushed = (digitalRead(clientpins::zoom_in_pin) == LOW);
  shared.zoom_out_pushed = (digitalRead(clientpins::zoom_out_pin) == LOW);

  // read the joystick button
  shared.joy_button_pushed = (digitalRead(clientpins::joy_button_pin) == LOW);

  // joystick speed, higher is faster
  const int16_t step = 64;

  // get the joystick movement, dividing by step discretizes it
  // currently a far joystick push will move the cursor about 5 pixels
  xy_pos delta(
    // the funny x/y swap is because of our joystick orientation
    (analogRead(clientpins::joy_y_pin)-shared.joy_centre.x)/step,
    (analogRead(clientpins::joy_x_pin)-shared.joy_centre.y)/step
  );
  delta.x = -delta.x; // horizontal axis is reversed in our orientation

  // check if there was enough movement to move the cursor
  if (delta.x != 0 || delta.y != 0) {
    // if we are here, there was noticeable movement

    // the next three functions are in map_drawing.h
    erase_cursor();       // erase the current cursor
    move_cursor(delta);   // move the cursor, and the map view if the edge was nudged
    if (shared.redraw_map == 0) {
      // it looks funny if we redraw the cursor before the map scrolls
      draw_cursor();      // draw the new cursor position
    }
  }
}


// following functions are for client code
//all must have timout funcationaltiy

void wait_for_ack(){
  
  int time = millis();
  while(time < 5000){


    if(Serial.available() > 0){

      char in_byte = Serial.read();

      if(in_byte == 'A'){
        curr_mode = SEND_DATA;
        Serial.write("A");
        Serial.write("\n");
        Serial.flush();
        break;

      }
      else{

        curr_mode = SEND_REQ;

      }

    }

  }
  
}


bool receive_data(){
  char buffer[129];
  int used = 0;
  int time = millis();

  int waypoint_number = 0;

  while(time < 5000){
    if(Serial.available() != 0){
      time = 0;
      time = millis();
      buffer[used] = Serial.read();
      Serial.print(buffer[used]);
      ++used;

      if (buffer[used-1] == '\n') {

        if(buffer[0] == 'N'){

          shared.num_waypoints = int(buffer[1]);

          if(shared.num_waypoints >= 500){
            shared.num_waypoints = 0;
          }
          used = 0;
        }
        else if(buffer[0] == 'W'){
          //waypoint
          int lon = 0;
          int lat = 0;
          for(int i = 1; i < used; ++i){
            //write waypoints to shared
            
            if(buffer[i] == ' '){
              for(int j = i; j < used; ++j){
                lon = lon + int(buffer[i]);
              }
              break;
            }
            else{
              lat = lat + int(buffer[i]);
            }
            
          }

          lon_lat_32 waypoint;
          waypoint.lat = lat;
          waypoint.lon = lon;
          shared.waypoints[waypoint_number] = waypoint;
          waypoint_number++;
          used = 0;
        }
        else if(buffer[0] == 'E'){
          return true;
        }
        else{
          Serial.println("what the fuck have you given me");
          curr_mode = SEND_REQ;
          return false;
        }
        
      }
    }
  }

  curr_mode = SEND_REQ;
  return false;
}

void send_data(lon_lat_32 start, lon_lat_32 end){;
  
  String out_string = String(start.lat) + " " + String(start.lon) +" " + String(end.lat) + " " + String(end.lon) + "\r\n"; 
    
  for(int i = 0; i<out_string.length(); ++i){
    Serial.write(out_string[i]);
  }
  
  curr_mode = RECIEVE_DATA;
}

// very simple finite state machine:
// which endpoint are we waiting for?


int main() {
  setup();

  // the two points that are clicked
  lon_lat_32 start, end;
  bool dataReceived = false;
  while (true) {
    // clear entries for new state
    shared.zoom_in_pushed = 0;
    shared.zoom_out_pushed = 0;
    shared.joy_button_pushed = 0;
    shared.redraw_map = 0;
    

    // reads the three buttons and joystick movement
    // updates the cursor view, map display, and sets the
    // shared.redraw_map flag to 1 if we have to redraw the whole map
    // NOTE: this only updates the internal values representing
    // the cursor and map view, the redrawing occurs at the end of this loop
    process_input();

    // if a zoom button was pushed, update the map and cursor view values
    // for that button push (still need to redraw at the end of this loop)
    // function zoom_map() is from map_drawing.h
    if (shared.zoom_in_pushed) {
      zoom_map(1);
      shared.redraw_map = 1;
    }
    else if (shared.zoom_out_pushed) {
      zoom_map(-1);
      shared.redraw_map = 1;
    }

    // if the joystick button was clicked
    if (shared.joy_button_pushed) {

      if (curr_mode == WAIT_FOR_START) {
        // if we were waiting for the start point, record it
        // and indicate we are waiting for the end point
        start = get_cursor_lonlat();
        curr_mode = WAIT_FOR_STOP;
        status_message("TO?");

        // wait until the joystick button is no longer pushed
        while (digitalRead(clientpins::joy_button_pin) == LOW) {}
      }
      else {
        // if we were waiting for the end point, record it
        // and then communicate with the server to get the path
        end = get_cursor_lonlat();
        curr_mode = SEND_REQ;
        // TODO: communicate with the server to get the waypoints
        // send req, wait for ack, send ack, send data, wait, draw
        while(!dataReceived){
            if(curr_mode == SEND_REQ){
              Serial.write("R");
              Serial.write("\n");
              Serial.flush();
              curr_mode = WAIT_FOR_ACK;
            }
            else if(curr_mode == WAIT_FOR_ACK){
              wait_for_ack();
            }
            else if(curr_mode == SEND_DATA){
              send_data(start,end);
            }
            else if(curr_mode == RECIEVE_DATA){
              dataReceived = receive_data();
            }
            
        }
          

        
        


        // now we have stored the path length in
        // shared.num_waypoints and the waypoints themselves in
        // the shared.waypoints[] array, switch back to asking for the
        // start point of a new request
        curr_mode = WAIT_FOR_START;

        // wait until the joystick button is no longer pushed
        while (digitalRead(clientpins::joy_button_pin) == LOW) {}
      }
    }

    if (shared.redraw_map) {
      // redraw the status message
      if (curr_mode == WAIT_FOR_START) {
        status_message("FROM?");
      }
      else {
        status_message("TO?");
      }

      // redraw the map and cursor
      draw_map();
      draw_cursor();

      // TODO: draw the route if there is one
      draw_route();
    }
  }

  Serial.flush();
  return 0;
}
