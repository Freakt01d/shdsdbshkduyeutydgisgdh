#include <LiquidCrystal.h>

// LCD: RS, E, D4, D5, D6, D7
LiquidCrystal lcd(12, 10, 6, 5, 4, 3);

const int flameSensorPin = 8;
const int isdPlayEPin = 2;

void setup() {
  pinMode(flameSensorPin, INPUT);
  pinMode(isdPlayEPin, OUTPUT);

  digitalWrite(isdPlayEPin, LOW);

  lcd.begin(16, 2); // 16 columns, 2 rows
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("System Ready");
}

void loop() {
  bool fireDetected = digitalRead(flameSensorPin) == LOW; // LOW = fire

  if (fireDetected) {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("!! FIRE ALERT !!");
    lcd.setCursor(0, 1);
    lcd.print("Evacuate Now!");

    // Play ISD1820 message
    digitalWrite(isdPlayEPin, HIGH);
    delay(200);
    digitalWrite(isdPlayEPin, LOW);

    delay(5000); // Delay to avoid repeat triggers
  } else {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("System Normal");
    lcd.setCursor(0, 1);
    lcd.print("Monitoring...");
    delay(1000);
  }
}