
AS := ca65
LD := ld65

export TOP_DIR := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))
export BIN_DIR := $(TOP_DIR)/bin
export BUILD_DIR := $(TOP_DIR)/build
export CONF_DIR := $(TOP_DIR)/conf
export INC_DIR := $(TOP_DIR)/include
export BINC_DIR := $(TOP_DIR)/binclude
export SRC_DIR := $(TOP_DIR)/src

SRC_SUB_DIRS := $(wildcard $(SRC_DIR)/*/)
# BUILD_SUB_DIRS := $(SRC_SUB_DIRS:$(SRC_DIR)/%=$(BUILD_DIR)/%)

LD_CONF := $(CONF_DIR)/ld.cfg

SRCS := $(wildcard $(SRC_DIR)/*.s) $(wildcard $(addsuffix /*.s, $(SRC_SUB_DIRS)))
OBJS := $(SRCS:$(SRC_DIR)/%.s=$(BUILD_DIR)/%.o)
INCS := $(wildcard $(INC_DIR)/*.inc)
BINCS := $(wildcard $(BINC_DIR)/*)

NAME := nanorails
ROM := $(BIN_DIR)/$(NAME).nes
DBG := $(ROM:%.nes=%.dbg)

AS_FLAGS := -I $(INC_DIR)
AS_FLAGS += --bin-include-dir $(BINC_DIR)
AS_FLAGS += --feature string_escapes
AS_FLAGS += --feature underline_in_numbers
AS_FLAGS += --debug-info

LD_FLAGS := --dbgfile $(DBG)
LD_FLAGS += -C $(LD_CONF)

.PHONY: all
all: $(ROM)

.PHONY: clean
clean:
	-rm -rf $(BUILD_DIR)
	-rm -rf $(BIN_DIR)

# link object and library files into a iNES file
$(ROM): $(OBJS) $(LD_CONF) $(BIN_DIR)
	$(LD) $(LD_FLAGS) -o $@ $(OBJS)

# assemble source files into objects
$(BUILD_DIR)/%.o: $(SRC_DIR)/%.s $(INCS) $(BINCS) $(BINC_DIR) $(BUILD_DIR)
	$(AS) $(AS_FLAGS) -o $@ $<

$(BUILD_DIR):
	-mkdir $@
# 	-mkdir $(BUILD_SUB_DIRS)

$(BIN_DIR):
	-mkdir $@

$(BINC_DIR):
	-mkdir $@
