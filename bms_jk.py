import serial
import time


def parse_cell_voltages(response):
    """
    Szuka w ramce znacznika 0x79 i jeśli znajdzie:
    - następny bajt = length (L)
    - potem L bajtów zawiera 3*n grup: [cell_idx][volt_hi][volt_lo]
    Zwraca listę (cell_idx, volt_mV, volt_V_str)
    """
    cells = []
    i = 0
    while i < len(response):
        if response[i] == 0x79 and i + 1 < len(response):
            length = response[i + 1]
            start = i + 2
            end = start + length
            if end > len(response):
                break
            data = response[start:end]
            for g in range(len(data) // 3):
                base = g * 3
                cell_idx = data[base]
                volt_hi = data[base + 1]
                volt_lo = data[base + 2]
                volt_mV = (volt_hi << 8) | volt_lo
                volt_V = volt_mV / 1000.0
                cells.append((cell_idx, volt_mV, f"{volt_V:.3f} V"))
            return i, length, cells
        i += 1
    return None


def find_data_in_frame(response, param_name):
    """Znajduje dane w ramce odpowiedzi (SOC, Voltage, Current, Temperature, Capacity)"""
    if len(response) < 12:
        return None

    for pos in range(len(response) - 2):
        try:
            b0 = response[pos]
            b1 = response[(pos + 1)]

            if param_name == "SOC" and 0 <= b0 <= 100:
                return pos, f"{b0}%", bytes([b0])

            elif param_name == "Voltage":
                raw = (b0 << 8) + b1
                voltage = raw * 0.01
                if 20 <= voltage <= 30:  # Napięcie LiFePO4
                    return pos, f"{voltage:.2f}V", bytes([b0, b1])

            elif param_name == "Current":
                raw = (b0 << 8) | b1
                sign = -1 if raw & 0x8000 else 1
                value = raw & 0x7FFF
                current = sign * value * 0.01
                if -200 <= current <= 200:
                    direction = "↗️" if current > 0 else "↘️"
                    return pos, f"{current:+.2f} A {direction}", bytes([b0, b1])
 
            elif param_name == "Temperature":
                raw = (b0 << 8) | b1
                if -40 <= raw <= 150:
                    return pos, f"{raw} °C", bytes([b0, b1])

        except:
            continue

    return None


def jk_bms_protocol_analyzer():
    print("🔍 JK BMS - ANALIZATOR PROTOKOŁU")
    print("=" * 60)

    port = "COM28"
    baud = 115200

    # ✅ Dodano: ramka 'AllStatus' do pełnego odczytu danych oraz 'CellVoltages' (0x79)
    commands = {
        "SOC": "4E57001300000000030300850000000068000001AB",
        "Voltage": "4E57001300000000030300830000000068000001A9",
        "Current": "4E57001300000000030300840000000068000001AA", 
        "Temperature": "4E57001300000000030300810000000068000001A7",
        "Capacity": "4E57001300000000030300AA0000000068000001D0",  # nie działa
        "CellVoltages": "4E570013000000000303007900000000680000019F",
    }

    try:
        ser = serial.Serial(port, baud, timeout=1, write_timeout=1)
        print(f"📡 Połączono z BMS na {port} @ {baud}")
        print("-" * 60)

        for name, cmd_hex in commands.items():
            print(f"\n🎯 {name}:")
            ser.reset_input_buffer()
            ser.write(bytes.fromhex(cmd_hex))
            time.sleep(0.5)

            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"   📦 Odebrano: {len(response)} bajtów")
                print(f"   🔢 HEX: {response.hex().upper()}")

                # Sprawdź czy ramka zawiera napięcia ogniw
                cellinfo = parse_cell_voltages(response)
                if cellinfo:
                    pos, length, cells = cellinfo
                    print(
                        f"   🔋 Zidentyfikowano blok napięć ogniw @ pos {pos}, len={length}"
                    )
                    for idx, mV, vstr in cells:
                        print(f"      Cell {idx}: {mV} mV -> {vstr}")

                found = find_data_in_frame(
                    response, name if name != "CellVoltages" else "Voltage"
                )
                if found:
                    pos, value, bytes_data = found
                    print(f"   ✅ {name} parsed:")
                    print(f"      📍 pos: {pos}, bytes: {bytes_data.hex().upper()}")
                    print(f"      💡 value: {value}")
                else:
                    print(f"   ℹ️  Nie wykryto standardowego pola dla {name}")
            else:
                print("   ⚠️  Brak odpowiedzi")

        ser.close()

    except Exception as e:
        print(f"💥 Błąd: {e}")


if __name__ == "__main__":
    jk_bms_protocol_analyzer()
