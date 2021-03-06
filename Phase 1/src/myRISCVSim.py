"""
The project is developed as part of Computer Architecture class.
Project Name: Functional Simulator for subset of RISC-V Processor

-------------------------------------------------
| Developer's Name   | Developer's Email ID     |
|-----------------------------------------------|
| Akhil Arya         | 2019csb1066@iitrpr.ac.in |
| Harshwardhan Kumar | 2019csb1089@iitrpr.ac.in |
| Krithika Goyal     | 2019csb1094@iitrpr.ac.in |
| Rhythm Jain        | 2019csb1111@iitrpr.ac.in |
| Tarun Singla       | 2019csb1126@iitrpr.ac.in |
-------------------------------------------------
"""

# myRISCVSim.py
# Purpose of this file: Implementation file for myRISCVSim

from collections import defaultdict
from sys import exit
import os
import csv

# Register file
R = [0]*32

# Clock
clock = 0

# Program Counter
PC = 0

# Memory
MEM = defaultdict(lambda: '00')

# Intermediate datapath and control path signals
instruction_word = 0
operand1 = 0
operand2 = 0
operation = ''
rd = 0
offset = 0
register_data = '0x00000000'
memory_address = 0
alu_control_signal = -1
is_mem = [-1, -1] # [-1/0/1(no memory operation/load/store), type of load/store if any]
write_back_signal = False
terminate = False
inc_select = 0
pc_select = 0
return_address = -1
pc_offset = 0


# Utility functions
def nhex(num):
    if num < 0:
        num += 2**32
    return hex(num)

def nint(s, base, bits=32):
    num = int(s, base)
    if num >= 2**(bits-1):
        num -= 2**bits
    return num

def sign_extend(data):
    if data[2] == '8' or data[2] == '9' or data[2] == 'a' or data[2] == 'b' or data[2] == 'c' or data[2] == 'd' or data[2] == 'e' or data[2] == 'f':
        data = data[:2] + (10 - len(data)) * 'f' + data[2:]
    else:
        data = data[:2] + (10 - len(data)) * '0' + data[2:]
    return data


# run_RISCVsim function
def run_RISCVsim():
    global clock
    while(1):
        fetch()
        decode()
        if terminate:
            return
        execute()
        if terminate:
            return
        mem()
        write_back()
        clock += 1
        if clock > 16:
            return
        print("CLOCK CYCLE:", clock, '\n')


# It is used to set the reset values
def reset_proc():
    for i in range(32):
        R[i] = '0x00000000'
    R[2] = '0x7FFFFFF0'
    R[3] = '0x10000000'


# load_program_memory reads the input memory, and populates the instruction memory
def load_program_memory(file_name):
    try:
        fp = open(file_name, 'r')
        for line in fp:
            tmp = line.split()
            if len(tmp) == 2:
                address, instruction = tmp[0], tmp[1]
                write_word(address, instruction)
        fp.close()
    except:
        print("ERROR: Error opening input .mc file\n")
        exit(1)


# Creates a "data_out.mc" file and writes the data memory in it. It also creates
# a reg_out.mc file and writes the contents of registers in it.
def write_data_memory():
    try:
        fp = open("data_out.mc", "w")
        out_tmp = []
        for i in range(268435456, 268468221, 4):
            out_tmp.append(
                hex(i) + ' 0x' + MEM[i + 3] + MEM[i + 2] + MEM[i + 1] + MEM[i] + '\n')
        fp.writelines(out_tmp)
        fp.close()
    except:
        print("ERROR: Error opening data_out.mc file for writing\n")

    try:
        fp = open("reg_out.mc", "w")
        out_tmp = []
        for i in range(32):
            out_tmp.append('x' + str(i) + ' ' + R[i] + '\n')
        fp.writelines(out_tmp)
        fp.close()
    except:
        print("ERROR: Error opening reg_out.mc file for writing\n")


# It is called to end the program and write the updated data memory in "data_out.mc" file
# and the register contents in the "reg_out.mc" file.
def swi_exit():
    global terminate
    write_data_memory()
    terminate = True


# Reads from the instruction memory and updates the instruction register
def fetch():
    global PC, instruction_word, inc_select, pc_select

    instruction_word = '0x' + MEM[PC + 3] + MEM[PC + 2] + MEM[PC + 1] + MEM[PC]
    print("FETCH: Fetch instruction", instruction_word, "from address", nhex(PC))
    inc_select = 0
    pc_select = 0


# Decodes the instruction and decides the operation to be performed in the execute stage; reads the operands from the register file.
def decode():
    global alu_control_signal, operation, operand1, operand2, instruction_word, rd, offset, register_data, memory_address, write_back_signal, PC, is_mem, MEM, R

    if instruction_word == '0x401080BB':
        print("END PROGRAM\n")
        swi_exit()
        return

    bin_instruction = bin(int(instruction_word[2:], 16))[2:]
    bin_instruction = (32 - len(bin_instruction)) * '0' + bin_instruction

    opcode = int(bin_instruction[25:32], 2)
    func3 = int(bin_instruction[17:20], 2)
    func7 = int(bin_instruction[0:7], 2)

    path = os.path.dirname(__file__)
    f = open(os.path.join(path,'Instruction_Set_List.csv'))
    instruction_set_list = list(csv.reader(f))
    f.close()

    match_found = False
    track = 0

    for ins in instruction_set_list:
        if track == 0:
            match_found = False
        elif ins[4] != 'NA' and [int(ins[2], 2), int(ins[3], 2), int(ins[4], 2)] == [opcode, func3, func7]:
            match_found = True
        elif ins[4] == 'NA' and ins[3] != 'NA' and [int(ins[2], 2), int(ins[3], 2)] == [opcode, func3]:
            match_found = True
        elif ins[4] == 'NA' and ins[3] == 'NA' and int(ins[2], 2) == opcode:
            match_found = True
        if match_found:
            break
        track += 1

    if not match_found:
        print("ERROR: Unidentifiable machine code!\n")
        swi_exit()
        return

    op_type = instruction_set_list[track][0]
    operation = instruction_set_list[track][1]
    alu_control_signal = track

    is_mem = [-1, -1]

    if op_type == 'R':
        rs2 = bin_instruction[7:12]
        rs1 = bin_instruction[12:17]
        rd = bin_instruction[20:25]
        operand1 = R[int(rs1, 2)]
        operand2 = R[int(rs2, 2)]
        write_back_signal = True
        print("DECODE: Operation is ", operation.upper(), ", first operand is R", str(int(rs1, 2)), ", second operand is R", str(int(rs2, 2)), ", destination register is R", str(int(rd, 2)), sep="")
        print("DECODE: Read registers: R", str(int(rs1, 2)), " = ", nint(operand1, 16), ", R", str(int(rs2, 2)), " = ", nint(operand2, 16), sep="")

    elif op_type == 'I':
        rs1 = bin_instruction[12:17]
        rd = bin_instruction[20:25]
        imm = bin_instruction[0:12]
        operand1 = R[int(rs1, 2)]
        operand2 = imm
        write_back_signal = True
        print("DECODE: Operation is ", operation.upper(), ", first operand is R", str(int(rs1, 2)), ", immediate is ", nint(operand2, 2, len(operand2)), ", destination register is R", str(int(rd, 2)), sep="")
        print("DECODE: Read registers: R", str(int(rs1, 2)), " = ", nint(operand1, 16), sep="")

    elif op_type == 'S':
        rs2 = bin_instruction[7:12]
        rs1 = bin_instruction[12:17]
        imm = bin_instruction[0:7] + bin_instruction[20:25]
        operand1 = R[int(rs1, 2)]
        operand2 = imm
        register_data = R[int(rs2, 2)]
        write_back_signal = False
        print("DECODE: Operation is ", operation.upper(), ", first operand is R", str(int(rs1, 2)), ", immediate is ", nint(operand2, 2, len(operand2)), ", data to be stored is in R", str(int(rs2, 2)), sep="")
        print("DECODE: Read registers: R", str(int(rs1, 2)), " = ", nint(operand1, 16), ", R", str(int(rs2, 2)), " = ", nint(register_data, 16), sep="")

    elif op_type == 'SB':
        rs2 = bin_instruction[7:12]
        rs1 = bin_instruction[12:17]
        operand1 = R[int(rs1, 2)]
        operand2 = R[int(rs2, 2)]
        imm = bin_instruction[0] + bin_instruction[24] + \
            bin_instruction[1:7] + bin_instruction[20:24] + '0'
        offset = imm
        write_back_signal = False
        print("DECODE: Operation is ", operation.upper(), ", first operand is R", str(int(rs1, 2)), ", second operand is R", str(int(rs2, 2)), ", immediate is ", nint(offset, 2, len(offset)), sep="")
        print("DECODE: Read registers: R", str(int(rs1, 2)), " = ", nint(operand1, 16), ", R", str(int(rs2, 2)), " = ", nint(operand2, 16), sep="")

    elif op_type == 'U':
        rd = bin_instruction[20:25]
        imm = bin_instruction[0:20]
        write_back_signal = True
        print("DECODE: Operation is ", operation.upper(), ", immediate is ", nint(imm, 2, len(imm)), ", destination register is R", str(int(rd, 2)), sep="")
        print("DECODE: No register read")
        imm += '0'*12
        operand2 = imm

    elif op_type == 'UJ':
        rd = bin_instruction[20:25]
        imm = bin_instruction[0] + bin_instruction[12:20] + \
            bin_instruction[11] + bin_instruction[1:11]
        write_back_signal = True
        print("DECODE: Operation is ", operation.upper(), ", immediate is ", nint(imm, 2, len(imm)), ", destination register is R", str(int(rd, 2)), sep="")
        print("DECODE: No register read")
        imm += '0'
        offset = imm

    else:
        print("ERROR: Unidentifiable machine code!\n")
        swi_exit()
        return


# Executes the ALU operation based on ALUop
def execute():
    global alu_control_signal, operation, operand1, operand2, instruction_word, rd, offset, register_data, memory_address, write_back_signal, PC, is_mem, MEM, R, pc_offset, pc_select, inc_select, return_address

    if alu_control_signal == 2:
        register_data = nhex(int(nint(operand1, 16) + nint(operand2, 16)))
        print("EXECUTE:", operation.upper(), nint(operand1, 16), "and", nint(operand2, 16))

    elif alu_control_signal == 8:
        register_data = nhex(int(nint(operand1, 16) - nint(operand2, 16)))
        print("EXECUTE:", operation.upper(), nint(operand1, 16), "and", nint(operand2, 16))

    elif alu_control_signal == 1:
        register_data = nhex(int(int(operand1, 16) & int(operand2, 16)))
        print("EXECUTE:", operation.upper(), nint(operand1, 16), "and", nint(operand2, 16))

    elif alu_control_signal == 3:
        register_data = nhex(int(int(operand1, 16) | int(operand2, 16)))
        print("EXECUTE:", operation.upper(), nint(operand1, 16), "and", nint(operand2, 16))

    elif alu_control_signal == 4:
        if(nint(operand2, 16) < 0):
            print("ERROR: Shift by negative!\n")
            swi_exit()
            return
        else:
            register_data = nhex(int(int(operand1, 16) << int(operand2, 16)))
            print("EXECUTE:", operation.upper(), nint(operand1, 16), "and", nint(operand2, 16))

    elif alu_control_signal == 5:
        if (nint(operand1, 16) < nint(operand2, 16)):
            register_data = hex(1)
        else:
            register_data = hex(0)
        print("EXECUTE:", operation.upper(), nint(operand1, 16), "and", nint(operand2, 16))

    elif alu_control_signal == 6:
        if(nint(operand2, 16) < 0):
            print("ERROR: Shift by negative!\n")
            swi_exit()
            return
        else:
            register_data = bin(int(int(operand1, 16) >> int(operand2, 16)))
            if operand1[2] == '8' or operand1[2] == '9' or operand1[2] == 'a' or operand1[2] == 'b' or operand1[2] == 'c' or operand1[2] == 'd' or operand1[2] == 'e' or operand1[2] == 'f':
                register_data = '0b' + (34 - len(register_data)) * '1' + register_data[2:]
            register_data = hex(int(register_data, 2))
            print("EXECUTE:", operation.upper(), nint(operand1, 16), "and", nint(operand2, 16))

    elif alu_control_signal == 7:
        if(nint(operand2, 16) < 0):
            print("ERROR: Shift by negative!\n")
            swi_exit()
            return
        else:
            register_data = nhex(int(operand1, 16) >> int(operand2, 16))
            print("EXECUTE:", operation.upper(), nint(operand1, 16), "and", nint(operand2, 16))

    elif alu_control_signal == 9:
        register_data = nhex(int(int(operand1, 16) ^ int(operand2, 16)))
        print("EXECUTE:", operation.upper(), nint(operand1, 16), "and", nint(operand2, 16))

    elif alu_control_signal == 10:
        register_data = nhex(int(nint(operand1, 16) * nint(operand2, 16)))
        print("EXECUTE:", operation.upper(), nint(operand1, 16), "and", nint(operand2, 16))

    elif alu_control_signal == 11:
        if nint(operand2, 16) == 0:
            print("ERROR: Division by zero!\n")
            swi_exit()
            return
        else:
            register_data = nhex(int(nint(operand1, 16) / nint(operand2, 16)))
            print("EXECUTE:", operation.upper(), nint(operand1, 16), "and", nint(operand2, 16))

    elif alu_control_signal == 12:
        register_data = nhex(int(nint(operand1, 16) % nint(operand2, 16)))
        print("EXECUTE:", operation.upper(), nint(operand1, 16), "and", nint(operand2, 16))

    elif alu_control_signal == 14:
        register_data = nhex(
            int(nint(operand1, 16) + nint(operand2, 2, len(operand2))))
        print("EXECUTE: ADD", int(operand1, 16), "and", nint(operand2, 2, len(operand2)))

    elif alu_control_signal == 13:
        register_data = nhex(int(int(operand1, 16) & int(operand2, 2)))
        print("EXECUTE: AND", int(operand1, 16), "and", nint(operand2, 2, len(operand2)))

    elif alu_control_signal == 15:
        register_data = nhex(int(int(operand1, 16) | int(operand2, 2)))
        print("EXECUTE: OR", int(operand1, 16), "and", nint(operand2, 2, len(operand2)))

    elif alu_control_signal == 16:
        memory_address = int(int(operand1, 16) + nint(operand2, 2, len(operand2)))
        is_mem = [0, 0]
        print("EXECUTE: ADD", int(operand1, 16), "and", nint(operand2, 2, len(operand2)))

    elif alu_control_signal == 17:
        memory_address = int(int(operand1, 16) + nint(operand2, 2, len(operand2)))
        is_mem = [0, 1]
        print("EXECUTE: ADD", int(operand1, 16), "and", nint(operand2, 2, len(operand2)))

    elif alu_control_signal == 18:
        memory_address = int(int(operand1, 16) + nint(operand2, 2, len(operand2)))
        is_mem = [0, 3]
        print("EXECUTE: ADD", int(operand1, 16), "and", nint(operand2, 2, len(operand2)))

    elif alu_control_signal == 19:
        register_data = nhex(PC + 4)
        return_address = nint(operand2, 2, len(operand2)) + nint(operand1, 16)
        pc_select = 1
        print("EXECUTE: No execute operation")

    elif alu_control_signal == 20:
        memory_address = int(int(operand1, 16) + nint(operand2, 2, len(operand2)))
        is_mem = [1, 0]
        print("EXECUTE: ADD", int(operand1, 16), "and", nint(operand2, 2, len(operand2)))

    elif alu_control_signal == 22:
        memory_address = int(int(operand1, 16) + nint(operand2, 2, len(operand2)))
        is_mem = [1, 1]
        print("EXECUTE: ADD", int(operand1, 16), "and", nint(operand2, 2, len(operand2)))

    elif alu_control_signal == 21:
        memory_address = int(int(operand1, 16) + nint(operand2, 2, len(operand2)))
        is_mem = [1, 3]
        print("EXECUTE: ADD", int(operand1, 16), "and", nint(operand2, 2, len(operand2)))

    elif alu_control_signal == 23:
        if nint(operand1, 16) == nint(operand2, 16):
            pc_offset = nint(offset, 2, len(offset))
            inc_select = 1
        print("EXECUTE:", operation.upper(), nint(operand1, 16), "and", nint(operand2, 16))

    elif alu_control_signal == 24:
        if nint(operand1, 16) != nint(operand2, 16):
            pc_offset = nint(offset, 2, len(offset))
            inc_select = 1
        print("EXECUTE:", operation.upper(), nint(operand1, 16), "and", nint(operand2, 16))

    elif alu_control_signal == 25:
        if nint(operand1, 16) >= nint(operand2, 16):
            pc_offset = nint(offset, 2,  len(offset))
            inc_select = 1
        print("EXECUTE:",  operation.upper(), nint(operand1, 16), "and", nint(operand2, 16))

    elif alu_control_signal == 26:
        if nint(operand1, 16) < nint(operand2, 16):
            pc_offset =  nint(offset, 2, len(offset))
            inc_select = 1
        print("EXECUTE:", operation.upper(), nint(operand1, 16), "and", nint(operand2, 16))

    elif alu_control_signal == 27:
        register_data = nhex(int(PC + 4 + int(operand2, 2)))
        print("EXECUTE: Shift left", int(operand2[0:20], 2), "by 12 bits and ADD", PC + 4)

    elif alu_control_signal == 28:
        register_data = nhex(int(operand2, 2))
        print("EXECUTE: Shift left", int(operand2[0:20], 2), "by 12 bits")

    elif alu_control_signal == 29:
        register_data = nhex(PC + 4)
        pc_offset = nint(offset, 2, len(offset))
        inc_select = 1
        print("EXECUTE: No execute operation")

    if len(register_data) > 10:
        register_data = register_data[:2] + register_data[-8:]

    register_data = register_data[:2] + \
        (10 - len(register_data)) * '0' + register_data[2::]


# Performs the memory operations and also performs the operations of IAG.
def mem():
    global operation, operand1, operand2, instruction_word, rd, offset, register_data, memory_address, write_back_signal, PC, is_mem, MEM, R, pc_offset, pc_select, return_address, inc_select

    if is_mem[0] == -1:
        print("MEMORY: No memory operation")

    elif is_mem[0] == 0:
        register_data = '0x'
        if is_mem[1] == 0:
            register_data += MEM[memory_address]
        elif is_mem[1] == 1:
            register_data += (MEM[memory_address + 1] + MEM[memory_address])
        else:
            register_data += (MEM[memory_address + 3] + MEM[memory_address + 2] + MEM[memory_address + 1] + MEM[memory_address])

        register_data = sign_extend(register_data)

        if is_mem[1] == 0:
            print("MEMORY: Load(byte)", nint(register_data, 16), "from", hex(memory_address))
        elif is_mem[1] == 1:
            print("MEMORY: Load(half-word)", nint(register_data, 16), "from", hex(memory_address))
        else:
            print("MEMORY: Load(word)", nint(register_data, 16), "from", hex(memory_address))

    else:
        if is_mem[1] >= 3:
            MEM[memory_address + 3] = register_data[2:4]
            MEM[memory_address + 2] = register_data[4:6]
        if is_mem[1] >= 1:
            MEM[memory_address + 1] = register_data[6:8]
        if is_mem[1] >= 0:
            MEM[memory_address] = register_data[8:10]

        if is_mem[1] == 0:
            print("MEMORY: Store(byte)", nint(register_data[8:10], 16), "to", hex(memory_address))
        elif is_mem[1] == 1:
            print("MEMORY: Store(half-word)", nint(register_data[6:10], 16), "to", hex(memory_address))
        else:
            print("MEMORY: Store(word)",  nint(register_data[2:10], 16), "to", hex(memory_address))

    if pc_select:
        PC = return_address
    elif inc_select:
        PC += pc_offset
    else:
        PC += 4


# Writes the results back to the register file
def write_back():
    if write_back_signal:
        if int(rd, 2) != 0:
            R[int(rd, 2)] = register_data
            print("WRITEBACK: Write", nint(register_data, 16), "to", "R" + str(int(rd, 2)))
        else:
            print("WRITEBACK: Value of R0 can not change")

    else:
        print("WRITEBACK: No write-back operation")


# Memory write
def write_word(address, instruction):
    idx = int(address[2:], 16)
    MEM[idx] =  instruction[8:10]
    MEM[idx + 1] = instruction[6:8]
    MEM[idx + 2] = instruction[4:6]
    MEM[idx + 3] = instruction[2:4]
