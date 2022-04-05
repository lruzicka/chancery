# Chancery

**Chancery** is a very simple text editor for openQA (https://open.qa), i.e. allows to type text, save and open files. However, its main purpose is to      speed up the development of openQA test scripts so it does not specialize in text typing in the first place. Its main strength is that it comes with a library of openQA command snippets that you can quickly insert using the *menu items* or *keyboard shortcuts*.

The current version (0.9) offers almost all snippets that are most frequently used in Fedora openQA scripts. The future versions will provide more and more    snippets until the whole openQA `TestApi <http://open.qa/api/testapi/>`_ is covered. If you are new to openQA scripting, you might want to read the `openQA    TestApi <http://open.qa/api/testapi/>`_ to understand, how specific methods (snippets) work and what you can expect from them.

## How to use the application

* Type in the text area.
* Insert snippets at a cursor position using **Quick actions**, **Menu**, or **keyboard shortcuts**.

## How to start with openQA scripting

1. Each script needs to be enclosed in the `sub {}` structure, or it will not work in the openQA engine. The **Create file layout** button in the **Quick      actions** will insert the snippet for you.

2. Each script needs to have a subroutine called `test_flags` to set test flags for the script. The **Set test flags** button in the **Quick actions** will insert the snippet for you with **all the test flags switched off**. To **switch on** the flag, change its value to `1`. Note, that some of the test flags contradict each other, such as `no_rollback` or `always_rollback` so pay close attention to the flag settings. Feel free to delete any unused flag. It will increase the script's readability.

## How to work with snippets

### Obligatory arguments

Usually, the methods use **obligatory arguments**, further called *arguments*. These are presented as **perl variables**, such as `$needlematch` or `$text`. You can define these variables before they are used, or replace their references with correct values.

### Non-obligatory arguments

The testAPI methods use various configuration options. When these are left out, the method then works with the default settings, which is mostly fine.
The snippets, however, provide all such configuration variables using the default values so they can be modified to suit the users' needs without having to consult the documentation all the time. If you *do not need to alter an option* you can leave it as is, or delete it from the snippet for better readability.

## How to report bugs

If you think you have found a bug, report it in the project's issues.

