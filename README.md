#include <LiquidCrystal.h>

// RS, E, D4, D5, D6, D7
LiquidCrystal lcd(8, 9, 4, 5, 6, 7);

const int flameSensorPin = 2;
const int isdPlayEPin = 3;
const int ledPin = 10;

void setup() {
  pinMode(flameSensorPin, INPUT);
  pinMode(isdPlayEPin, OUTPUT);
  pinMode(ledPin, OUTPUT);

  digitalWrite(isdPlayEPin, LOW);
  digitalWrite(ledPin, LOW);

  lcd.begin(16, 2); // 16 columns, 2 rows
  lcd.setCursor(0, 0);
  lcd.print(" System Ready ");
}

void loop() {
  bool fireDetected = digitalRead(flameSensorPin) == LOW; // LOW = fire

  if (fireDetected) {
    digitalWrite(ledPin, HIGH);  // Turn on fire LED

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("!! FIRE ALERT !!");
    lcd.setCursor(0, 1);
    lcd.print("Evacuate Now!");

    // Trigger ISD1820 playback
    digitalWrite(isdPlayEPin, HIGH);
    delay(150);
    digitalWrite(isdPlayEPin, LOW);

    delay(5000);  // Wait to avoid retrigger
  } else {
    digitalWrite(ledPin, LOW);  // Turn off LED

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print(" System Normal ");
    lcd.setCursor(0, 1);
    lcd.print("Monitoring...  ");
    delay(1000);
  }
}