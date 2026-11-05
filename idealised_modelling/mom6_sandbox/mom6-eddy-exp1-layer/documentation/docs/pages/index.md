
Welcome to the documentation for the [mom6-idealised ocean model configurations](https://github.com/ACCESS-Community-Hub/mom6-idealised-configs)! 

The purpose of this repository, is to encourage community users to both use and share _idealised_ ocean model configurations.

## Getting involved in mom6-idealised

**Contributions from people of all career stages and backgrounds are highly encouraged.** All these models and configurations are developed are open source. Development is led by ACCESS-NRI and the [COSIMA working group](https://cosima.org.au/) where we follow an open development model building on the work of international modelling consortia.

Contributors so far include: Christopher Bull (ACCESS-NRI), Claire Yung (Australian National University), Josef Bisits (University of New South Wales).

### Report a bug or make a suggestion

Technical issues related to mom6-idealised are best posted to [github.com/ACCESS-NRI/mom6-idealised-configs/issues](https://github.com/ACCESS-Community-Hub/mom6-idealised-configs/issues). If you would like to discuss the issue first, feel free to post it on the [access hive forum](https://forum.access-hive.org.au/c/cosima/29).

### Add a new iOM3 configuration

There are several different ways to do this depending on the kind of contribution. Best to get in touch on the [access hive forum](https://forum.access-hive.org.au/c/cosima/29), ping @ACCESS-NRI/ocean on GitHub or email `chris.bull@anu.edu.au`.

### mom6-idealised documentation

We appreciate contributions, typo and bugs fixes to this documentation. To make suggestions please see steps below.

#### Quick contributions 
!!! tip
    This method has the advantage is that it's *very quick* (<1 minute!). The caveat is that, unless you have write access to the `mom6-idealised-configs` repository, you will not be able to preview the changes rendered into a website or create whole new pages. <br>

The simplest and fastest way to make a change to an _existing_ page is to click the edit "pencil" on the top-right corner. This will go to the relevant GitHub markdown file and clicking the _top-right pencil again_ on GitHub will allow you to edit the file. Once complete, click `Commit changes...`. There are then _two_ possibilities, depending on whether you have  write access to [`mom6-idealised-configs`](https://github.com/ACCESS-Community-Hub/mom6-idealised-configs): 

1.  **No write access**: this will prompt you to make a fork and then a pull request (less than 1 minute!). 
1.  **You have write access**: please commit changes on a new branch and then use a pull request (this relates to the next option). 

#### Larger contributions (online PR-previews)
!!! tip
    This method allows you create whole new pages, and to preview the changes rendered into a website. It does not require you to install any software, but is **only available for people with write access to [`mom6-idealised-configs`](https://github.com/ACCESS-Community-Hub/mom6-idealised-configs)**.<br>

Create a new branch, e.g. `jblogs/doc-update`, make doc changes (the documentation sources are in [github.com/ACCESS-NRI/mom6-idealised-configs/tree/main/documentation](https://github.com/ACCESS-Community-Hub/mom6-idealised-configs/tree/main/documentation)), then open a related PR and a GitHub preview will be made automatically.

#### Larger contributions (`mkdocs` offline)
!!! tip
    Similar to the above, this method allows you create whole new pages and to preview the changes rendered into a website. It works whether or not you have write access to [`mom6-idealised-configs`](https://github.com/ACCESS-Community-Hub/mom6-idealised-configs), but requires you to install `mkdocs` and takes the longest to set up.<br>

Following [these instructions](https://docs.access-hive.org.au/about/contribute/#lets-get-started) but noting the documentation sources are in [github.com/ACCESS-Community-Hub/mom6-idealised-configs](https://github.com/ACCESS-Community-Hub/mom6-idealised-configs). You’ll need to fork the [ACCESS-Hive Docs GitHub repository](https://github.com/ACCESS-NRI/access-hive.org.au) and clone it locally if you want to write your own content. Once cloned, make sure to invoke `mkdocs serve` from within the `documentation` directory.

Additional steps and contribution guidelines can be found [here](https://docs.access-hive.org.au/about/contribute/#clone-the-forked-access-hive-docs-github-repository-locally).

If you want to add a new page, then you need to add another markdown file in the folder (or sub-folder as appropriate):
[github.com/ACCESS-NRI/mom6-idealised-configs/tree/main/documentation/docs/pages](https://github.com/ACCESS-Community-Hub/mom6-idealised-configs/tree/main/documentation/docs/pages)

Once done, update the documentation navigation in [github.com/ACCESS-NRI/mom6-idealised-configs/blob/main/documentation/mkdocs.yml](https://github.com/ACCESS-Community-Hub/mom6-idealised-configs/blob/main/documentation/mkdocs.yml) by adding an entry under the `nav:` section. Note you'll need to add the sub-folder paths as appropriate.


