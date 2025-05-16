#include "clang/Frontend/CompilerInstance.h"
#include "clang/Tooling/CommonOptionsParser.h"
#include "clang/AST/ASTConsumer.h"
#include "clang/Tooling/Tooling.h"
#include "clang/AST/RecursiveASTVisitor.h"
#include "clang/AST/PrettyPrinter.h"
#include "clang/Frontend/FrontendAction.h"
#include "clang/CodeGen/CodeGenAction.h"

#include "llvm/IR/DebugInfoMetadata.h"
#include "llvm/Analysis/CallGraph.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"
#include "llvm/Support/VirtualFileSystem.h"
#include "llvm/Support/ToolOutputFile.h"
#include "llvm/Bitcode/BitcodeWriter.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/InstrTypes.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/DerivedTypes.h"

#include "llvm/Target/TargetMachine.h"
#include "llvm/Support/FileSystem.h"
#include "llvm/Support/TargetRegistry.h"
#include "llvm/Support/TargetSelect.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/Support/Host.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Linker/Linker.h"

#include "nlohmann/json.hpp"

#include <iostream>
#include <fstream>
#include <unordered_set>

using namespace clang;
using namespace clang::tooling;
using namespace clang::driver;
using namespace llvm;
using json = nlohmann::json;

static llvm::cl::OptionCategory FindFunctionCategory("");

class FunctionVisitor : public RecursiveASTVisitor<FunctionVisitor> {
    public:
        explicit FunctionVisitor(ASTContext *_context, CompilerInstance &_compiler)
        : context(_context), compiler(_compiler) {}

		bool VisitFunctionDecl(FunctionDecl *function) {
    
			std::string functionName = function->getNameInfo().getName().getAsString();
		
			if (functionName == "main") {
				// Here we are assuming that `main` is not called by any other functions
				// If it is, then we need to make this modification while generating the CFG
				// instead of patching it here.
				functionName = "main_0"; // Rename main to main_0
			}
		
			SourceLocation startLocation = function->getBeginLoc();
			SourceManager &SM = context->getSourceManager();
			startLocation = SM.getFileLoc(startLocation); // To compensate for macros
			FullSourceLoc startLoc = context->getFullLoc(startLocation);
			FullSourceLoc endLoc = context->getFullLoc(function->getEndLoc());
		
			if (!startLoc.isValid() || !endLoc.isValid()) {
				return true;
			}
		
			if (SM.isInSystemHeader(startLoc)) {
				return true;
			}
			if (function->isThisDeclarationADefinition()) {
				int startLine = startLoc.getSpellingLineNumber();
				int endLine = endLoc.getSpellingLineNumber();
				int startCol = startLoc.getSpellingColumnNumber();
				int endCol = endLoc.getSpellingColumnNumber();
		
				// Get file name
				std::string fileName = SM.getFilename(startLocation).str();
				
				PrintingPolicy Policy(context->getLangOpts());
				std::string returnType = function->getReturnType().getAsString(Policy);
				std::string signature = returnType + " " + function->getQualifiedNameAsString() + "(";
		
				for (unsigned i = 0; i < function->getNumParams(); ++i) {
					if (i > 0) {
						signature += ", ";
					}
					ParmVarDecl *param = function->getParamDecl(i);
					std::string paramType = param->getType().getAsString(Policy);
					std::string paramName = param->getNameAsString();
		
					signature += paramType;
					if (!paramName.empty()) { // Only add name if it exists
						signature += " " + paramName;
					}
				}
				signature += ")";
		
				// Add this info to the json data
				json functionData = {
						{"name", functionName},
						{"signature", signature},
						{"filename", fileName},
						{"startLine", startLine},
						{"endLine", endLine},
						{"startCol", startCol},
						{"endCol", endCol}
				};
				this->data.insert(functionData);
			}
			return true;
		}

        std::unordered_set<json> getData() {
            return data;
        }

    private:
        ASTContext *context;
        CompilerInstance &compiler;
        std::unordered_set<json> data;
};

class FunctionVisitorConsumer : public ASTConsumer {
    public:
        explicit FunctionVisitorConsumer(ASTContext *context,
                                         CompilerInstance &compiler,
                                         std::unique_ptr<ASTConsumer> defaultConsumer)
                : visitor(context, compiler), defaultConsumer(std::move(defaultConsumer)) {}
    
		void HandleTranslationUnit(ASTContext &context) {
			visitor.TraverseDecl(context.getTranslationUnitDecl());
			data = visitor.getData();
			defaultConsumer->HandleTranslationUnit(context);
		}

        std::unordered_set<json> getData() {
            return data;
        }
    
        // Here we forward the calls to the default consumer
        // Ugly, but I don't know a better way
        void Initialize(ASTContext &Context) { defaultConsumer->Initialize(Context); }
        bool HandleTopLevelDecl(DeclGroupRef D) { return defaultConsumer->HandleTopLevelDecl(D); }
        void HandleInlineFunctionDefinition(FunctionDecl *D) { defaultConsumer->HandleInlineFunctionDefinition(D); }
        void HandleInterestingDecl(DeclGroupRef D) { defaultConsumer->HandleInterestingDecl(D); }
        void HandleTagDeclDefinition(TagDecl *D) { defaultConsumer->HandleTagDeclDefinition(D); }
        void HandleTagDeclRequiredDefinition(const TagDecl *D) { defaultConsumer->HandleTagDeclRequiredDefinition(D); }
        void HandleCXXImplicitFunctionInstantiation(FunctionDecl *D) { defaultConsumer->HandleCXXImplicitFunctionInstantiation(D); }
        void HandleTopLevelDeclInObjCContainer(DeclGroupRef D) { defaultConsumer->HandleTopLevelDeclInObjCContainer(D); }
        void HandleImplicitImportDecl(ImportDecl *D) { defaultConsumer->HandleImplicitImportDecl(D); }
        void CompleteTentativeDefinition(VarDecl *D) { defaultConsumer->CompleteTentativeDefinition(D); }
        void CompleteExternalDeclaration(VarDecl *D) { defaultConsumer->CompleteExternalDeclaration(D); }
        void AssignInheritanceModel(CXXRecordDecl *RD) { defaultConsumer->AssignInheritanceModel(RD); }
        void HandleCXXStaticMemberVarInstantiation(VarDecl *D) { defaultConsumer->HandleCXXStaticMemberVarInstantiation(D); }
        void HandleVTable(CXXRecordDecl *RD) { defaultConsumer->HandleVTable(RD); }
        ASTMutationListener *GetASTMutationListener() { return defaultConsumer->GetASTMutationListener(); }
        ASTDeserializationListener *GetASTDeserializationListener() { return defaultConsumer->GetASTDeserializationListener(); }
        void PrintStats() { defaultConsumer->PrintStats(); }
        bool shouldSkipFunctionBody(Decl *D) { return defaultConsumer->shouldSkipFunctionBody(D); }
    
    private:
        FunctionVisitor visitor;
        std::unique_ptr<ASTConsumer> defaultConsumer;
        std::unordered_set<json> data;
};

class FunctionVisitAction : public EmitLLVMOnlyAction {
    public:
		std::unique_ptr<ASTConsumer>
		CreateASTConsumer(CompilerInstance &compiler, llvm::StringRef inFile) {
			std::unique_ptr<ASTConsumer> defaultConsumer(
				EmitLLVMOnlyAction::CreateASTConsumer(compiler, inFile));
		
			return std::make_unique<FunctionVisitorConsumer>(
				&compiler.getASTContext(), compiler, std::move(defaultConsumer));
		}
		
		void EndSourceFileAction() {
			// First call the base class implementation
			EmitLLVMOnlyAction::EndSourceFileAction();
		
			// Next, retrieve the ASTConsumer so that we can get the stored data
			CompilerInstance &compiler = this->getCompilerInstance();
			if (!compiler.hasASTConsumer()) {
				std::cerr << "No ASTConsumer\n";
				return;
			}
			FunctionVisitorConsumer &myConsumer = dynamic_cast<FunctionVisitorConsumer&>(compiler.getASTConsumer());
			std::unordered_set<json> fileData = myConsumer.getData();
			// Append the updated data to this->data
			for (const auto &entry : fileData) {
				this->data.insert(entry);
			}
			// Get the generated module and add it to the list
			std::unique_ptr<llvm::Module> M = this->takeModule();
			if (!M) {
				std::cerr << "Failed to generate module\n";
				return;
			}
			if (linker == nullptr) {
				this->mod = std::move(M);
				linker = new llvm::Linker(*(this->mod));
			} else {
				if (linker->linkInModule(std::move(M))) {
					std::cerr << "Error linking module\n";
					return;
				}
			}
		}
    
        std::unordered_set<json> getData() {
            return data;
        }
        std::unique_ptr<llvm::Module> getModule() {
            return std::move(mod);
        }
    
    private:
        std::unordered_set<json> data;
        std::unique_ptr<llvm::Module> mod;
        llvm::Linker* linker = nullptr;
};


class ToolActionWrapper: public tooling::FrontendActionFactory {
    public:
        explicit ToolActionWrapper(FrontendAction *action)
            : action(action) {}
        
        FrontendAction *getAction() {
            return action;
        }
    
		// Ideally this function should never be called
		std::unique_ptr<FrontendAction> create() {
			std::cerr << "create() should not be called in ToolActionWrapper\n";
			// This is just a placeholder to satisfy the interface
			return std::unique_ptr<FrontendAction>(action);
		}

		// Modified from FrontendActionFactory::runInvocation
		bool runInvocation(
				std::shared_ptr<CompilerInvocation> Invocation,
				FileManager *Files,
				std::shared_ptr<PCHContainerOperations> PCHContainerOps,
				DiagnosticConsumer *DiagConsumer) {

			CompilerInstance Compiler(std::move(PCHContainerOps));
			Compiler.setInvocation(std::move(Invocation));
			Compiler.setFileManager(Files);
			
			// Compile with debug info
			CodeGenOptions &CGOpts = Compiler.getCodeGenOpts();
			CGOpts.setDebugInfo(codegenoptions::FullDebugInfo);
			CGOpts.RelocationModel = llvm::Reloc::PIC_;
			CGOpts.OptimizationLevel = 0;
			
			// Create the compiler's actual diagnostics engine.
			Compiler.createDiagnostics(DiagConsumer, /*ShouldOwnClient=*/false);
			if (!Compiler.hasDiagnostics())
				return false;
			
			Compiler.createSourceManager(*Files);
			
			const bool Success = Compiler.ExecuteAction(*action);
			
			Files->clearStatCache();
			return Success;
		}
    
    private:
        FrontendAction *action;
};

void addInstrumentation(llvm::Module &M) {
	// Add instrumentation code to the module
	LLVMContext &Context = M.getContext();
	IRBuilder<> Builder(Context);
	
	// Declare standard library functions
	FunctionCallee Getenv = M.getOrInsertFunction(
        "getenv", llvm::FunctionType::get(llvm::PointerType::get(llvm::Type::getInt8Ty(Context), 0),
                                    {llvm::PointerType::get(llvm::Type::getInt8Ty(Context), 0)}, false));

	FunctionCallee Snprintf = M.getOrInsertFunction(
		"snprintf", llvm::FunctionType::get(llvm::IntegerType::getInt32Ty(Context),
									{llvm::PointerType::get(llvm::Type::getInt8Ty(Context), 0),
										llvm::IntegerType::getInt64Ty(Context),
										llvm::PointerType::get(llvm::Type::getInt8Ty(Context), 0),
										llvm::PointerType::get(llvm::Type::getInt8Ty(Context), 0)},
									true));

	FunctionCallee Fopen = M.getOrInsertFunction(
		"fopen", llvm::FunctionType::get(llvm::PointerType::get(llvm::Type::getInt8Ty(Context), 0),
									{llvm::PointerType::get(llvm::Type::getInt8Ty(Context), 0),
									llvm::PointerType::get(llvm::Type::getInt8Ty(Context), 0)}, false));

	FunctionCallee Fprintf = M.getOrInsertFunction(
		"fprintf", llvm::FunctionType::get(llvm::IntegerType::getInt32Ty(Context),
									{llvm::PointerType::get(llvm::Type::getInt8Ty(Context), 0),
									llvm::PointerType::get(llvm::Type::getInt8Ty(Context), 0)}, true));

	FunctionCallee Fclose = M.getOrInsertFunction(
		"fclose", llvm::FunctionType::get(llvm::IntegerType::getInt32Ty(Context),
									{llvm::PointerType::get(llvm::Type::getInt8Ty(Context), 0)}, false));

	// Iterate over all functions in the module
	for (Function &F : M) {
		// Skip functions that are not defined in the module
		if (F.isDeclaration()) continue;

		Builder.SetInsertPoint(&*F.getEntryBlock().getFirstInsertionPt());

		// Get environment variable
		Value *EnvVarName = Builder.CreateGlobalStringPtr("INSTRUMENTATION_PATH");
		Value *DirPath = Builder.CreateCall(Getenv, {EnvVarName});
		Value *DefaultPath = Builder.CreateGlobalStringPtr("./instrumented.json");

		// Check if INSTRUMENTATION_PATH is set
		Value *IsEnvSet = Builder.CreateICmpNE(DirPath, llvm::ConstantPointerNull::get(cast<llvm::PointerType>(DirPath->getType())));

		// Allocate buffer for full path
		Value *FullPathBuffer = Builder.CreateAlloca(llvm::ArrayType::get(llvm::Type::getInt8Ty(Context), 512));

		// Convert FullPathBuffer to i8* (char*)
		Value *FullPathPtr = Builder.CreateBitCast(FullPathBuffer, llvm::Type::getInt8PtrTy(Context));

		// Format string: "%s/instrumented.json"
		Value *FormatStr = Builder.CreateGlobalStringPtr("%s/instrumented.json");

		// Concatenate path using snprintf
		Builder.CreateCall(Snprintf, {FullPathPtr, ConstantInt::get(llvm::Type::getInt64Ty(Context), 512),
																	FormatStr, DirPath});

		// Use CreateSelect with correctly typed pointers
		Value *FinalFilePath = Builder.CreateSelect(IsEnvSet, FullPathPtr, DefaultPath);
		
		// Open file in append mode
		Value *Mode = Builder.CreateGlobalStringPtr("a");
		Value *FilePtr = Builder.CreateCall(Fopen, {FinalFilePath, Mode});

		std::string jsonStr = "{ \"name\": \"" + F.getName().str() + "\", \"args\": [";
		std::vector<Value *> PrintArgs;
		
		for (auto &Arg : F.args()) {
			llvm::Type *ArgType = Arg.getType();
	
			if (ArgType->isIntegerTy()) {
					jsonStr += "\"%d\", ";
					PrintArgs.push_back(&Arg);
			} else if (ArgType->isFloatingPointTy()) {
					jsonStr += "\"%f\", ";
					Value *DoubleVal = Builder.CreateFPExt(&Arg, llvm::Type::getDoubleTy(Context));
					PrintArgs.push_back(DoubleVal);
			} else if (ArgType->isPointerTy()) {
					llvm::Type *ElemType = ArgType->getPointerElementType();
					
					if (ElemType->isIntegerTy(8)) { // char* (i8*)
							jsonStr += "\"%.100s\", ";  // Limit to 100 chars
							PrintArgs.push_back(&Arg);
					} else {
							jsonStr += "\"%p\", ";
							PrintArgs.push_back(&Arg);
					}
			} else {
					jsonStr += "\"<unsupported>\", ";
			}
		}
		
		if (!PrintArgs.empty()) jsonStr.pop_back(), jsonStr.pop_back();
		jsonStr += "], \"return\": [";

		// Insert before return instructions
		for (auto &BB : F) {
			if (ReturnInst *Ret = dyn_cast<ReturnInst>(BB.getTerminator())) {
				Builder.SetInsertPoint(Ret);
				Value *RetVal = Ret->getReturnValue();
				if (RetVal) {
					if (F.getReturnType()->isIntegerTy()) {
						jsonStr += "\"%d\"";
						PrintArgs.push_back(RetVal);
					} else if (F.getReturnType()->isFloatingPointTy()) {
						jsonStr += "\"%f\"";
						Value *DoubleVal = Builder.CreateFPExt(RetVal, llvm::Type::getDoubleTy(Context));
						PrintArgs.push_back(DoubleVal);
					} else if (F.getReturnType()->isPointerTy()) {
                        llvm::Type *ElemType = F.getReturnType()->getPointerElementType();
					
                        if (ElemType->isIntegerTy(8)) { // char* (i8*)
                                jsonStr += "\"%.100s\", ";  // Limit to 100 chars
                                PrintArgs.push_back(RetVal);
                        } else {
                                jsonStr += "\"%p\", ";
                                PrintArgs.push_back(RetVal);
                        }
					} else {
						jsonStr += "\"<unsupported>\"";
					}
				}
				jsonStr += "] },\n";

				// Write to file
				Constant *JsonFormatStr = Builder.CreateGlobalStringPtr(jsonStr);
				std::vector<Value *> FprintfArgs = {FilePtr, JsonFormatStr};
				FprintfArgs.insert(FprintfArgs.end(), PrintArgs.begin(), PrintArgs.end());
				Builder.CreateCall(Fprintf, FprintfArgs);
			}
		}

		// Close file
		Builder.CreateCall(Fclose, {FilePtr});
	}
}

bool compareFilenames(std::string filename1, std::string filename2) {
	// Compare the filenames without the path
	std::string baseName1 = llvm::sys::path::filename(filename1);
	std::string baseName2 = llvm::sys::path::filename(filename2);
	return baseName1 == baseName2;
}

int main(int argc, const char **argv) {
	auto expectedParser = CommonOptionsParser::create(argc, argv, FindFunctionCategory, llvm::cl::ZeroOrMore, "ast-visitor <source0> [... <sourceN>] --");
	if (!expectedParser) {
		llvm::errs() << expectedParser.takeError();
		return 1;
	}

	CommonOptionsParser& optionsParser = expectedParser.get();
	ClangTool tool(optionsParser.getCompilations(),
				   optionsParser.getSourcePathList());
	ToolActionWrapper actionWrapper(new FunctionVisitAction());
	tool.run(&actionWrapper);
	
	FunctionVisitAction *action = static_cast<FunctionVisitAction*>(actionWrapper.getAction());
	std::unique_ptr<llvm::Module> M = action->getModule();
	std::unordered_set<json> jsonData = action->getData();

	// Rename main as main_0 to avoid clash with main in Rust
	llvm::Function *MainFunc = M.get()->getFunction("main");
	if (MainFunc) {
		MainFunc->setName("main_0");
		if (llvm::DISubprogram *SP = MainFunc->getSubprogram()) {
			llvm::LLVMContext &Ctx = M.get()->getContext();
			SP->replaceOperandWith(2, llvm::MDString::get(Ctx, "main_0"));
		}
		std::cout << "Renamed function: main -> main_0\n";
	}

	// Run a CallGraphAnalysis pass on M
	llvm::PassBuilder PB;
	llvm::ModuleAnalysisManager MAM;
	PB.registerModuleAnalyses(MAM);
	llvm::CallGraph &CG = MAM.getResult<llvm::CallGraphAnalysis>(*M);

	for (llvm::Function &F : M->functions()) {
		if (F.isDeclaration()){
			continue; // Skip declarations without a body
		}
		// Get the subprogram that contains the function
		llvm::DISubprogram *SubProg = F.getSubprogram();
		if (!SubProg){
			continue; // Skip functions without debug info
		}
		const llvm::Function *constFunctionPtr = &F;
		// Store all the functions that are called by the current function
		std::set<std::string> calledFunctions = {};
		for (auto &I : *CG[constFunctionPtr]) {
			if (I.second && I.second->getFunction()) {
				if (!I.second->getFunction()->isDeclaration()) {
					calledFunctions.insert(I.second->getFunction()->getName().str());
				}
			}
		}
		for (auto &entry : jsonData) {
			if (entry["name"] == F.getName() &&
				compareFilenames(entry["filename"], SubProg->getFilename())) {
				auto mutableEntry = entry;
				mutableEntry["calledFunctions"] = calledFunctions;
				// Update the entry in the set
				jsonData.erase(entry);
				jsonData.insert(mutableEntry);
				break;
			}
		}
	}
	// Write this jsonData to a file functions.json
	std::ofstream outFile("functions.json");
	if (outFile.is_open()) {
		outFile << std::setw(4) << jsonData << std::endl;
		outFile.close();
		std::cout << "Data written to functions.json\n";
	} else {
		std::cerr << "Unable to open file functions.json\n";
		return 1;
	}
	// Add instrumentation to the module
	addInstrumentation(*M);

	std::error_code EC;
	llvm::legacy::PassManager PM;
	std::string ErrorMessage;  // Use std::string for the error message

	// Write the module to an .ll file
	// llvm::raw_fd_ostream IRFile("instrumented.ll", EC);
	// M->print(IRFile, nullptr);

    std::string TargetTriple = llvm::sys::getDefaultTargetTriple();

    llvm::raw_fd_ostream ObjFile("instrumented.o", EC, llvm::sys::fs::OF_None);

    // Initialize all target-related information
    llvm::InitializeAllTargetInfos();           // Initialize all target infos
    llvm::InitializeAllTargets();               // Initialize all targets
    llvm::InitializeAllTargetMCs();             // Initialize all target machine code generation
    llvm::InitializeAllAsmParsers();            // Initialize all assembly parsers
    llvm::InitializeAllAsmPrinters();           // Initialize all assembly printers

    // Look up the target based on the triple string
    const llvm::Target* Target = llvm::TargetRegistry::lookupTarget(TargetTriple, ErrorMessage);

    if (!Target) {
        llvm::errs() << "Error: " << ErrorMessage << "\n";
        return 1;
    }

    // Now proceed with creating the TargetMachine and generating the object file as usual
	auto RM = llvm::Optional<llvm::Reloc::Model>(llvm::Reloc::PIC_);
    llvm::TargetOptions Options;
    auto TM = Target->createTargetMachine(TargetTriple, "generic", "", Options, RM);

    M->setDataLayout(TM->createDataLayout());
    if (TM->addPassesToEmitFile(PM, ObjFile, nullptr, llvm::CGFT_ObjectFile)) {
        llvm::errs() << "TargetMachine can't emit object file!\n";
    }

    PM.run(*M);
    ObjFile.close();
	// std::cout << "Instrumented object file written to instrumented.o\n";

	 // Invoke `ar` to create a static library
	 int result = std::system("ar rcs libfoo.a instrumented.o");
	 if (result != 0) {
		 llvm::errs() << "Failed to create static library\n";
		 return 1;
	 }
	 std::cout << "Static library created: libfoo.a\n";
	 // Clean up the object file
	 EC = llvm::sys::fs::remove("instrumented.o", false);
	 if (EC) {
		 llvm::errs() << "Failed to remove object file: " << EC.message() << "\n";
		 return 1;
	 }
	 return 0;
}