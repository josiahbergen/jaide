"""Integration tests: assemble snippets, load into emulator, step through, verify state."""

from jaide.constants import FLAG_C, FLAG_Z, FLAG_N, FLAG_O


class TestMov:

    def test_mov_immediate(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x0042")
        emu.step()
        assert emu.reg["A"].value == 0x0042

    def test_mov_reg_to_reg(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x00FF\nmov B, A")
        emu.step()
        emu.step()
        assert emu.reg["B"].value == 0x00FF

    def test_mov_large_immediate(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0xBEEF")
        emu.step()
        assert emu.reg["A"].value == 0xBEEF


class TestArithmetic:

    def test_add_reg_reg(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x000A\nmov B, 0x0014\nadd A, B")
        for _ in range(3):
            emu.step()
        assert emu.reg["A"].value == 30

    def test_add_reg_imm(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x0005\nadd A, 0x0003")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 8

    def test_sub_reg_reg(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x0064\nmov B, 0x0032\nsub A, B")
        for _ in range(3):
            emu.step()
        assert emu.reg["A"].value == 50

    def test_sub_sets_zero(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x0005\nsub A, 0x0005")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0
        assert emu.flag_get(FLAG_Z)

    def test_inc(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x0009\ninc A")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 10

    def test_dec(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x000A\ndec A")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 9


class TestBitwise:

    def test_and(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x00FF\nand A, 0x000F")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0x000F

    def test_or(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x00F0\nor A, 0x000F")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0x00FF

    def test_xor(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x00FF\nxor A, 0x00FF")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0

    def test_not(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x00FF\nnot A")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0xFF00

    def test_lsh(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x0001\nlsh A, 0x0004")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0x0010

    def test_rsh(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x0100\nrsh A, 0x0004")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0x0010


class TestStack:

    def test_push_pop(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x1234\npush A\nmov A, 0x0000\npop B")
        for _ in range(4):
            emu.step()
        assert emu.reg["B"].value == 0x1234
        assert emu.reg["A"].value == 0

    def test_push_immediate(self, assemble_and_load):
        emu = assemble_and_load("push 0xABCD\npop A")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0xABCD


class TestMemory:

    def test_put_get(self, assemble_and_load):
        emu = assemble_and_load(
            "mov A, 0x5000\n"   # address
            "mov B, 0xCAFE\n"   # value
            "put [A], B\n"      # store
            "mov B, 0x0000\n"   # clear B
            "get C, [A]\n"      # load
        )
        for _ in range(5):
            emu.step()
        assert emu.reg["C"].value == 0xCAFE


class TestJump:

    def test_jmp_skips(self, assemble_and_load):
        # jmp over the first mov to A, so A stays 0 and B gets set
        src = (
            "jmp skip\n"
            "mov A, 0x00FF\n"
            "skip:\n"
            "mov B, 0x0042\n"
        )
        emu = assemble_and_load(src)
        emu.step()  # jmp
        emu.step()  # mov B
        assert emu.reg["A"].value == 0
        assert emu.reg["B"].value == 0x0042

    def test_jz_taken(self, assemble_and_load):
        src = (
            "mov A, 0x0001\n"
            "sub A, 0x0001\n"  # A=0, zero flag set
            "jz done\n"
            "mov B, 0x00FF\n"  # should be skipped
            "done:\n"
            "mov C, 0x0042\n"
        )
        emu = assemble_and_load(src)
        for _ in range(4):
            emu.step()
        assert emu.reg["B"].value == 0  # skipped
        assert emu.reg["C"].value == 0x0042

    def test_jnz_not_taken(self, assemble_and_load):
        src = (
            "mov A, 0x0001\n"
            "sub A, 0x0001\n"  # zero flag set
            "jnz skip\n"
            "mov B, 0x0042\n"  # should execute
            "skip:\n"
            "nop\n"
        )
        emu = assemble_and_load(src)
        for _ in range(4):
            emu.step()
        assert emu.reg["B"].value == 0x0042


class TestCallRet:

    def test_call_and_ret(self, assemble_and_load):
        src = (
            "call myfunc\n"
            "mov B, 0x0042\n"  # return here
            "jmp done\n"
            "myfunc:\n"
            "mov A, 0x00FF\n"
            "ret\n"
            "done:\n"
            "nop\n"
        )
        emu = assemble_and_load(src)
        emu.step()  # call myfunc
        emu.step()  # mov A, 0xFF
        emu.step()  # ret
        emu.step()  # mov B, 0x42
        assert emu.reg["A"].value == 0x00FF
        assert emu.reg["B"].value == 0x0042


class TestDiv:

    def test_div_reg_reg(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x000A\nmov B, 0x0003\ndiv A, B")
        for _ in range(3):
            emu.step()
        assert emu.reg["A"].value == 3  # 10 // 3

    def test_div_reg_imm(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x000C\ndiv A, 0x0004")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 3

    def test_div_sets_zero_flag(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x0003\ndiv A, 0x0004")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0
        assert emu.flag_get(FLAG_Z)

    def test_div_carry_set_when_remainder(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x000A\ndiv A, 0x0003")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 3
        assert emu.flag_get(FLAG_C)  # remainder = 1

    def test_div_carry_clear_when_exact(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x0009\ndiv A, 0x0003")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 3
        assert not emu.flag_get(FLAG_C)  # remainder = 0


class TestAsr:

    def test_asr_reg_imm_positive(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x0010\nasr A, 0x0002")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0x0004

    def test_asr_preserves_sign(self, assemble_and_load):
        # 0x8000 >> 1 = 0xC000 (sign extended, not 0x4000 as logical shift would give)
        emu = assemble_and_load("mov A, 0x8000\nasr A, 0x0001")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0xC000

    def test_asr_reg_reg(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x0080\nmov B, 0x0003\nasr A, B")
        for _ in range(3):
            emu.step()
        assert emu.reg["A"].value == 0x0010

    def test_asr_negative_fills_ones(self, assemble_and_load):
        # 0xFFFF (-1) >> 4 == 0xFFFF
        emu = assemble_and_load("mov A, 0xFFFF\nasr A, 0x0004")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0xFFFF


class TestPutRelPointer:

    def test_put_label_stores_value(self, assemble_and_load_ram):
        src = (
            "mov A, 0x00FF\n"
            "put [myvar], A\n"
            "jmp done\n"
            "myvar:\n"
            "DATA 0x0000\n"
            "done:\n"
            "get B, [myvar]\n"
        )
        emu = assemble_and_load_ram(src)
        emu.step()  # mov A
        emu.step()  # put [myvar], A
        emu.step()  # jmp done
        emu.step()  # get B, [myvar]
        assert emu.reg["B"].value == 0x00FF


class TestSwp:

    def test_swp_swaps_registers(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x1111\nmov B, 0x2222\nswp A, B")
        for _ in range(3):
            emu.step()
        assert emu.reg["A"].value == 0x2222
        assert emu.reg["B"].value == 0x1111

    def test_swp_same_register(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x00FF\nswp A, A")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0x00FF


# ---------------------------------------------------------------------------
# Instructions not yet covered above
# ---------------------------------------------------------------------------

class TestNop:

    def test_nop_advances_pc(self, assemble_and_load):
        emu = assemble_and_load("nop")
        pc_before = emu.pc.value
        emu.step()
        assert emu.pc.value == pc_before + 1  # NOP is 1 word


class TestHalt:

    def test_halt_sets_waiting(self, assemble_and_load):
        emu = assemble_and_load("halt\nmov A, 0x00FF")
        emu.step()
        assert emu.waiting_for_interrupt  # HALT waits for interrupt

    def test_halt_does_not_execute_next(self, assemble_and_load):
        emu = assemble_and_load("halt\nmov A, 0x00FF")
        emu.step()  # halt
        # interrupt never arrives, so next step sleeps and returns without decoding
        emu.step()
        assert emu.reg["A"].value == 0  # mov A never ran


class TestMovLabel:

    def test_mov_loads_label_address(self, assemble_and_load):
        # MOV A, label loads the absolute word address of label into A
        src = (
            "mov A, target\n"
            "jmp done\n"
            "target:\n"
            "nop\n"
            "done:\n"
            "nop\n"
        )
        emu = assemble_and_load(src)
        emu.step()  # mov A, target  (target is at word 3)
        # words: mov(0-1) jmp(2-3) target:/nop(4) done:/nop(5)
        # mov next_pc=2, target=4, imm=(4-2)=2 → A = pc(2) + 2 = 4
        assert emu.reg["A"].value == 4


class TestAdc:

    def test_adc_without_carry(self, assemble_and_load):
        # carry flag is 0 → adc behaves like add
        emu = assemble_and_load("mov A, 0x0005\nadc A, 0x0003")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 8

    def test_adc_with_carry(self, assemble_and_load):
        # set carry via add overflow, then adc adds the carry in
        src = (
            "mov A, 0xFFFF\n"
            "add A, 0x0001\n"  # result=0, carry=1
            "mov B, 0x0005\n"
            "adc B, 0x0003\n"  # B = 5 + 3 + 1 = 9
        )
        emu = assemble_and_load(src)
        for _ in range(4):
            emu.step()
        assert emu.reg["B"].value == 9

    def test_adc_reg_reg(self, assemble_and_load):
        src = (
            "mov A, 0xFFFF\n"
            "add A, 0x0001\n"  # carry = 1
            "mov B, 0x0010\n"
            "mov C, 0x0001\n"
            "adc B, C\n"       # B = 0x10 + 1 + 1(carry) = 0x12
        )
        emu = assemble_and_load(src)
        for _ in range(5):
            emu.step()
        assert emu.reg["B"].value == 0x12


class TestSbc:

    def test_sbc_carry_clear(self, assemble_and_load):
        # FLAG_C=0 at init → borrow_in=0 → SBC does dest - src - 0
        emu = assemble_and_load("mov A, 0x000A\nsbc A, 0x0003")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 7  # 10 - 3 - 0 = 7

    def test_sbc_carry_set(self, assemble_and_load):
        # FLAG_C=1 (set by a no-borrow sub) → borrow_in=1 → SBC does dest - src - 1
        src = (
            "mov A, 0x000A\n"
            "sub A, 0x0005\n"  # 10-5=5, no borrow → carry=1
            "mov B, 0x000A\n"
            "sbc B, 0x0003\n"  # B = 10 - 3 - 1 = 6
        )
        emu = assemble_and_load(src)
        for _ in range(4):
            emu.step()
        assert emu.reg["B"].value == 6

    def test_sbc_reg_reg(self, assemble_and_load):
        src = (
            "mov A, 0x000A\n"
            "sub A, 0x0005\n"  # carry=1
            "mov B, 0x000A\n"
            "mov C, 0x0002\n"
            "sbc B, C\n"       # B = 10 - 2 - 1 = 7
        )
        emu = assemble_and_load(src)
        for _ in range(5):
            emu.step()
        assert emu.reg["B"].value == 7


class TestMul:

    def test_mul_reg_imm(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x0006\nmul A, 0x0007")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 42

    def test_mul_reg_reg(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x0003\nmov B, 0x0004\nmul A, B")
        for _ in range(3):
            emu.step()
        assert emu.reg["A"].value == 12

    def test_mul_overflow_sets_carry(self, assemble_and_load):
        # 0x0100 * 0x0100 = 0x10000 → result=0, carry=1
        emu = assemble_and_load("mov A, 0x0100\nmul A, 0x0100")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0
        assert emu.flag_get(FLAG_C)

    def test_mul_no_overflow(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x00FF\nmul A, 0x0001")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0x00FF
        assert not emu.flag_get(FLAG_C)


class TestMod:

    def test_mod_reg_imm(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x000A\nmod A, 0x0003")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 1  # 10 % 3 = 1

    def test_mod_reg_reg(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x000B\nmov B, 0x0004\nmod A, B")
        for _ in range(3):
            emu.step()
        assert emu.reg["A"].value == 3  # 11 % 4 = 3

    def test_mod_exact(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x0009\nmod A, 0x0003")
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0
        assert emu.flag_get(FLAG_Z)

    def test_mod_by_zero_queues_interrupt(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x0005\nmod A, 0x0000")
        emu.step()
        emu.step()  # mod by zero → queues interrupt vector 0
        assert 0 in emu.pending_interrupts
        assert emu.reg["A"].value == 5  # dest unchanged


class TestGetVariants:

    def test_get_rel_pointer(self, assemble_and_load):
        # GET A, [label] — PC-relative load
        src = (
            "get A, [mydata]\n"
            "jmp done\n"
            "mydata:\n"
            "DATA 0x00FF\n"
            "done:\n"
            "nop\n"
        )
        emu = assemble_and_load(src)
        emu.step()
        assert emu.reg["A"].value == 0x00FF

    def test_get_off_pointer(self, assemble_and_load):
        # GET A, [label + B] — offset load (array indexing)
        src = (
            "mov B, 0x0001\n"
            "get A, [arr + B]\n"
            "jmp done\n"
            "arr:\n"
            "DATA 0x0011\n"
            "DATA 0x0022\n"
            "done:\n"
            "nop\n"
        )
        emu = assemble_and_load(src)
        emu.step()  # mov B, 1
        emu.step()  # get A, [arr + B]  → arr[1] = 0x0022
        assert emu.reg["A"].value == 0x0022

    def test_get_off_pointer_zero_offset(self, assemble_and_load):
        src = (
            "mov B, 0x0000\n"
            "get A, [arr + B]\n"
            "jmp done\n"
            "arr:\n"
            "DATA 0x00AB\n"
            "done:\n"
            "nop\n"
        )
        emu = assemble_and_load(src)
        emu.step()
        emu.step()
        assert emu.reg["A"].value == 0x00AB


class TestPutOffPointer:

    def test_put_off_pointer(self, assemble_and_load_ram):
        # PUT [label + B], A — offset store
        src = (
            "mov A, 0xBEEF\n"
            "mov B, 0x0001\n"
            "put [arr + B], A\n"
            "jmp done\n"
            "arr:\n"
            "DATA 0x0000\n"
            "DATA 0x0000\n"
            "done:\n"
            "mov B, 0x0001\n"
            "get C, [arr + B]\n"
        )
        emu = assemble_and_load_ram(src)
        emu.step()  # mov A
        emu.step()  # mov B, 1
        emu.step()  # put [arr+1], A
        emu.step()  # jmp done
        emu.step()  # mov B, 1 (reload — B was 1 already, but explicit)
        emu.step()  # get C, [arr+1]
        assert emu.reg["C"].value == 0xBEEF


class TestBitwiseRegReg:

    def test_and_reg_reg(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x00FF\nmov B, 0x0F0F\nand A, B")
        for _ in range(3):
            emu.step()
        assert emu.reg["A"].value == 0x000F

    def test_or_reg_reg(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x00F0\nmov B, 0x000F\nor A, B")
        for _ in range(3):
            emu.step()
        assert emu.reg["A"].value == 0x00FF

    def test_xor_reg_reg(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0xAAAA\nmov B, 0x5555\nxor A, B")
        for _ in range(3):
            emu.step()
        assert emu.reg["A"].value == 0xFFFF

    def test_lsh_reg_reg(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x0001\nmov B, 0x0004\nlsh A, B")
        for _ in range(3):
            emu.step()
        assert emu.reg["A"].value == 0x0010

    def test_rsh_reg_reg(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x0080\nmov B, 0x0003\nrsh A, B")
        for _ in range(3):
            emu.step()
        assert emu.reg["A"].value == 0x0010


class TestCmp:

    def test_cmp_sets_zero_when_equal(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x0005\nmov B, 0x0005\ncmp A, B")
        for _ in range(3):
            emu.step()
        assert emu.flag_get(FLAG_Z)

    def test_cmp_sets_carry_no_borrow(self, assemble_and_load):
        # A > B → no borrow → C=1
        emu = assemble_and_load("mov A, 0x0007\nmov B, 0x0003\ncmp A, B")
        for _ in range(3):
            emu.step()
        assert emu.flag_get(FLAG_C)
        assert not emu.flag_get(FLAG_Z)

    def test_cmp_clears_carry_on_borrow(self, assemble_and_load):
        # A < B → borrow → C=0
        emu = assemble_and_load("mov A, 0x0003\nmov B, 0x0007\ncmp A, B")
        for _ in range(3):
            emu.step()
        assert not emu.flag_get(FLAG_C)

    def test_cmp_does_not_modify_dest(self, assemble_and_load):
        emu = assemble_and_load("mov A, 0x1234\nmov B, 0x0001\ncmp A, B")
        for _ in range(3):
            emu.step()
        assert emu.reg["A"].value == 0x1234  # unchanged

    def test_cmp_imm(self, assemble_and_load):
        # cmp A, imm: uses A as dest (register 0 coincides with ssss slot)
        emu = assemble_and_load("mov A, 0x0005\ncmp A, 0x0005")
        emu.step()
        emu.step()
        assert emu.flag_get(FLAG_Z)


class TestJmpVariants:

    def test_jmp_reg(self, assemble_and_load):
        # mov A, 5  (A = word address 5)
        # jmp A     (jump to word 5)
        # mov B, 0x00FF  (words 3-4, skipped)
        # mov C, 0x0042  (words 5-6, executed)
        src = (
            "mov A, 0x0005\n"
            "jmp A\n"
            "mov B, 0x00FF\n"
            "mov C, 0x0042\n"
        )
        emu = assemble_and_load(src)
        emu.step()  # mov A, 5
        emu.step()  # jmp A
        emu.step()  # mov C, 0x0042 (at word 5)
        assert emu.reg["B"].value == 0     # skipped
        assert emu.reg["C"].value == 0x0042

    def test_jmp_imm(self, assemble_and_load):
        # jmp 4  (skip words 2-3)
        # mov A, 0x00FF  (words 2-3, skipped)
        # mov B, 0x0042  (words 4-5, executed)
        src = (
            "jmp 0x0004\n"
            "mov A, 0x00FF\n"
            "mov B, 0x0042\n"
        )
        emu = assemble_and_load(src)
        emu.step()  # jmp 4
        emu.step()  # mov B, 0x0042
        assert emu.reg["A"].value == 0
        assert emu.reg["B"].value == 0x0042


# ---------------------------------------------------------------------------
# Conditional jumps — each tested taken and not-taken
# ---------------------------------------------------------------------------

def _cond_jump_src(cmp_a, cmp_b, jump_mnemonic):
    """Return JASM source that sets C=2 if jump taken, C=1 if not."""
    return (
        f"mov A, {cmp_a}\n"
        f"mov B, {cmp_b}\n"
        "cmp A, B\n"
        f"{jump_mnemonic} taken\n"
        "mov C, 0x0001\n"
        "jmp done\n"
        "taken:\n"
        "mov C, 0x0002\n"
        "done:\n"
        "nop\n"
    )


class TestConditionalJumps:

    def _run(self, assemble_and_load, cmp_a, cmp_b, mnemonic):
        emu = assemble_and_load(_cond_jump_src(cmp_a, cmp_b, mnemonic))
        for _ in range(5):
            emu.step()
        return emu.reg["C"].value

    # JZ / JNZ

    def test_jz_taken(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0005", "0x0005", "jz") == 2

    def test_jz_not_taken(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0005", "0x0003", "jz") == 1

    def test_jnz_taken(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0005", "0x0003", "jnz") == 2

    def test_jnz_not_taken(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0005", "0x0005", "jnz") == 1

    # JC / JNC  (C=1 when A>=B unsigned, i.e. no borrow)

    def test_jc_taken(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0005", "0x0003", "jc") == 2

    def test_jc_not_taken(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0003", "0x0005", "jc") == 1

    def test_jnc_taken(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0003", "0x0005", "jnc") == 2

    def test_jnc_not_taken(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0005", "0x0003", "jnc") == 1

    # JA / JAE  (unsigned above / above-or-equal)

    def test_ja_taken(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0005", "0x0003", "ja") == 2

    def test_ja_not_taken_equal(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0003", "0x0003", "ja") == 1

    def test_jae_taken(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0005", "0x0003", "jae") == 2

    def test_jae_taken_equal(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0003", "0x0003", "jae") == 2

    def test_jae_not_taken(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0003", "0x0005", "jae") == 1

    # JB / JBE  (unsigned below / below-or-equal)

    def test_jb_taken(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0003", "0x0005", "jb") == 2

    def test_jb_not_taken(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0005", "0x0003", "jb") == 1

    def test_jbe_taken_less(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0003", "0x0005", "jbe") == 2

    def test_jbe_taken_equal(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0003", "0x0003", "jbe") == 2

    def test_jbe_not_taken(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0005", "0x0003", "jbe") == 1

    # JG / JGE  (signed greater / greater-or-equal)

    def test_jg_taken(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0005", "0x0003", "jg") == 2

    def test_jg_not_taken_equal(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0003", "0x0003", "jg") == 1

    def test_jg_not_taken_less(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0003", "0x0005", "jg") == 1

    def test_jge_taken(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0005", "0x0003", "jge") == 2

    def test_jge_taken_equal(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0003", "0x0003", "jge") == 2

    def test_jge_not_taken(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0003", "0x0005", "jge") == 1

    # JL / JLE  (signed less / less-or-equal)

    def test_jl_taken(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0003", "0x0005", "jl") == 2

    def test_jl_not_taken(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0005", "0x0003", "jl") == 1

    def test_jle_taken_less(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0003", "0x0005", "jle") == 2

    def test_jle_taken_equal(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0003", "0x0003", "jle") == 2

    def test_jle_not_taken(self, assemble_and_load):
        assert self._run(assemble_and_load, "0x0005", "0x0003", "jle") == 1


class TestCallReg:

    def test_call_reg(self, assemble_and_load):
        # mov A, myfunc  → A = absolute address of myfunc
        # call A         → push return addr, jump to myfunc
        # mov B, 0x0042  → executed after ret
        # jmp done
        # myfunc: mov A, 0x00FF; ret
        # done: nop
        src = (
            "mov A, myfunc\n"
            "call A\n"
            "mov B, 0x0042\n"
            "jmp done\n"
            "myfunc:\n"
            "mov A, 0x00FF\n"
            "ret\n"
            "done:\n"
            "nop\n"
        )
        emu = assemble_and_load(src)
        emu.step()  # mov A, myfunc  (A = word address of myfunc)
        emu.step()  # call A
        emu.step()  # mov A, 0x00FF  (in myfunc)
        emu.step()  # ret
        emu.step()  # mov B, 0x0042  (back in caller)
        assert emu.reg["A"].value == 0x00FF
        assert emu.reg["B"].value == 0x0042


class TestInbOutb:

    def test_outb_imm_reg(self, assemble_and_load):
        # outb 0x05, A  — write A to port 5
        emu = assemble_and_load("mov A, 0x00FF\noutb 0x05, A")
        emu.step()
        emu.step()
        assert emu.ports[5] == 0x00FF

    def test_outb_reg_reg(self, assemble_and_load):
        # outb B, A  — write A to port held in B
        emu = assemble_and_load("mov A, 0x1234\nmov B, 0x0007\noutb B, A")
        for _ in range(3):
            emu.step()
        assert emu.ports[7] == 0x1234

    def test_inb_reg_imm(self, assemble_and_load):
        # inb A, 0x05  — read port 5 into A
        emu = assemble_and_load("inb A, 0x05")
        emu.ports[5] = 0x00AB
        emu.step()
        assert emu.reg["A"].value == 0x00AB

    def test_inb_reg_reg(self, assemble_and_load):
        # inb A, B  — read port held in B into A
        emu = assemble_and_load("mov B, 0x0003\ninb A, B")
        emu.ports[3] = 0x00CD
        emu.step()  # mov B, 3
        emu.step()  # inb A, B
        assert emu.reg["A"].value == 0x00CD


class TestIntIret:

    def test_int_imm_jumps_to_handler(self, assemble_and_load):
        # Layout (assembled at word 0):
        #   word 0-1: int 200
        #   word 2-3: mov B, 0x00FF  (reached after iret)
        #   word 4:   halt
        #   word 5-6: mov A, 0x0042  (handler)
        #   word 7:   iret
        src = (
            "int 200\n"
            "mov B, 0x00FF\n"
            "halt\n"
            "handler:\n"
            "mov A, 0x0042\n"
            "iret\n"
        )
        emu = assemble_and_load(src)
        emu.write16(0xFFFF - 200, 5)   # vector 200 → handler at word 5
        emu.step()  # int 200 → jumps to 5, pushes PC=2 and flags
        emu.step()  # mov A, 0x0042
        emu.step()  # iret → restores flags and PC=2
        emu.step()  # mov B, 0x00FF
        assert emu.reg["A"].value == 0x0042
        assert emu.reg["B"].value == 0x00FF

    def test_int_reg(self, assemble_and_load):
        # Same as above but using INT A (register mode)
        src = (
            "mov A, 200\n"
            "int A\n"
            "mov B, 0x00FF\n"
            "halt\n"
            "handler:\n"
            "mov A, 0x0042\n"
            "iret\n"
        )
        emu = assemble_and_load(src)
        # Layout: mov(0-1) int(2) mov_B(3-4) halt(5) handler: mov_A(6-7) iret(8)
        emu.write16(0xFFFF - 200, 6)   # vector 200 → handler at word 6
        emu.step()  # mov A, 200
        emu.step()  # int A → jumps to 6, pushes PC=3
        emu.step()  # mov A, 0x0042
        emu.step()  # iret → PC=3
        emu.step()  # mov B, 0x00FF
        assert emu.reg["A"].value == 0x0042
        assert emu.reg["B"].value == 0x00FF

    def test_iret_restores_flags(self, assemble_and_load):
        # After IRET, the flags register should be exactly what it was before INT
        src = (
            "int 200\n"
            "halt\n"
            "handler:\n"
            "iret\n"
        )
        emu = assemble_and_load(src)
        # Layout: int(0-1) halt(2) handler: iret(3)
        emu.write16(0xFFFF - 200, 3)
        flags_before = emu.f.value
        emu.step()  # int 200
        emu.step()  # iret
        assert emu.f.value == flags_before
